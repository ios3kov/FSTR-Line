# Native subscription ABI triage — 2026-09-29

Run: `NATIVE-ABI-20260929-01`. Baseline `99d40f983f061d4357aa14c99985132096ab161d`.
Scope: read-only symbol inspection of installed macOS arm64 AE modules, no
process attach, patch, subscription, project access or security changes.
Objective: distinguish a callable subscription from previously observed change
functions. Acceptance requires known registration, callback, ownership,
disconnect and context-acquisition contracts before a native callback is called.

## Identity and procedure

The installed module SHA-256 values match the original research:

- BEE.dylib: `817b9de9c6d57b5d6988b634842090e1528fe817a5685c8d1ff358553c6660ca`.
- AfterFXLib: `ce3aa2f16fe5449a77379a6b622e1a221596e511b86f7708dd3e2f7a3cced01a`.

These hashes identify files on disk, not a currently loaded process.
Additional inspected dvacore framework SHA-256:
`cb6faaf5b745903b80b44105b658ab68186d5065ae47c8a57c9b23e26aa8ecb0`.
Used `xcrun nm -arch arm64 -gU` and `c++filt` to inspect defined external
symbols, and `xcrun llvm-objdump --macho --arch=arm64 --disassemble
--dis-symname SYMBOL MODULE` for selected functions. No LLDB process was used.
An initial address-range objdump invocation ignored the intended range in
Mach-O mode and produced excessive output; its output is not used as bounded
evidence. The corrected symbol-specific invocation is the reproducible path.

## Candidate findings

| Candidate / arm64 address | Observed fact | Remaining source gate |
| --- | --- | --- |
| `BEE_WorkQueue_RegisterListener` / `0x7eaa3c` and `BEE_WorkQueue_DeregisterListener` / `0x7eac80` | Exported registration takes a Boost function containing `ItemChangeType` and `boost::shared_ptr<BEE_WorkQueue_Item>`; registration creates a GUID and stores a copied callback under a lock | Work-item coverage is not Timeline coverage. Exact Boost ABI, lifetime, callback thread, disconnect synchronization and full change matrix are unknown |
| `BEE_Project::ConnectDirtyStateChangedSignal` / `0x3a6bc0` | Exported member takes `std::__1::function<void(BEE_Project*, bool)>`. Static body calls `dvacore::messaging::Signal<...>::Connect`, forwards indirect-return storage in x8, and operates on a project member | Return/connection ownership and safe project-object acquisition are unknown. Repeated dirty edits, selection and playhead coverage are unproved; a dirty flag alone is insufficient evidence |
| `BEE_UndoContext::GetUndoCommandCompletedSignal` / `0x64a6fc` | Exact body adds `0xd8` to the supplied object pointer and returns; starting-signal getter also exists | This is a member accessor, not a C callback registrar. Signal type/layout, context acquisition and safe detach are unknown; no coverage proof for changes outside Undo transactions |
| `CEggApp::GetProjectOpenedSignal` / `0x738fac`, activation signal / `0x738f98` | Defined external symbols in AfterFXLib | Context-only leads; no complete layer change subscription established |

The inspected SDK 25.6 public `AE_GeneralPlug.h` still exposes command/menu/
death/idle registration and the render-queue listener. It does not provide the
above private class/function/connection declarations. Mangled names encode
some argument types but do not supply ownership or the complete return ABI.

Further symbol-specific inspection narrows the dirty-signal return type:
its `Signal::Connect` implementation calls
`dvacore::messaging::Connection::Connection(std::__1::weak_ptr<ConnectionLink>)`
at BEE `0x3a6e88`, using the caller's indirect-return storage. In the inspected
dvacore binary that constructor writes a vtable pointer followed by a 16-byte
weak-pointer representation. `Connection::Disconnect()` is exported at
`0x1826ac`; it locks the weak pointer and invokes a virtual method on the link.
`ScopedConnection` constructors, destructor and assignment are exported too.
`BroadcastDirtyState` calls the same project's bool-valued signal directly.

Thus a concrete connection family and disconnect entry point are now located.
This does not establish full object layout across builds, synchronization with
an in-flight callback, safe destruction of client closures, or acquisition of a
live project pointer. No guessed C++ class was instantiated. Callback thread
and repeated dirty-state emission still need evidence; no runtime acceptance
follows from this static inspection.

## Decision

Follow-up native client and lifetime evidence:
`NATIVE-SUBSCRIPTION-LIFETIME-2026-09-29.md`. It narrows owner/disconnect
semantics without establishing a safe shipping ABI or complete source.

Static discovery PASS for these narrow facts. Native subscription execution
NOT RUN. No candidate is selected for production: casting a guessed prototype
to one of these symbols would skip the callback/return/lifetime safety gate.
Exact-build checks alone cannot make a wrong ABI safe.

Prefer investigating an actual connect/disconnect path over assuming that a
detour at `DoProcessProjectChanges` is a complete notification source. The
work-queue listener is a separate research lead, not accepted as Timeline
delivery. Do not substitute dirty-state polling or periodic reads.

Next bounded research: trace the native client's construction, connection and
destruction of a mutation signal, establish the connection type and ownership,
and locate its producer call sites. Require an ABI/ownership fixture and a
disposable native harness before invoking any private function in AE. If no
safe complete source can be established, keep production integration BLOCKED.
Compatibility, maintenance and applicable licensing review remain NOT RUN;
no third-party hook library or private native code was added to the product.
