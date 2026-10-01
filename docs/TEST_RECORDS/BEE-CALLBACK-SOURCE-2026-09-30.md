# BEE UI callback chain: an exported source candidate

Run: `BEE-CALLBACK-SOURCE-20260930-01`. Baseline: `cfa8a1db2fcd576a0023cdee579c7f83c40d04e6`.
Branch: `integration/host-safety-notifications`; PR #2 remains Draft/unmerged.
Phase 0: 0/5 accepted. Main rules blob: `701a8c1ae3acb4dbfe1d7eda94acbf8095b88608`.
Scope: static source/ABI investigation, not implementation or runtime acceptance.
No Adobe code loaded/executed, debugger attach, installation or project access.

## Question and acceptance for this research step

Find an externally resolvable registration/removal pair, its actual native client,
its callback forwarding contract, and concrete producers for repeated edits.
Require exact supplied-module identity, file-backed instruction checks and a
producer-to-dispatcher path, not symbol names alone. Stop expanding the completion
Signal template if no external registrar is available; investigate a simpler
existing source. Do not introduce guessed private classes or call internal addresses.

## Result: another route, not a completion-Signal workaround

BEE exports both of these exact Mach-O symbols:

```
__Z19BEE_Callback_InsertPFiR19BEE_FilterFuncChainI9BEE_CBMsgPvES1_S0_S1_ES1_
__Z19BEE_Callback_Removei
```

`Insert` starts at BEE `0x333624`; `Remove` at `0x333774`. They are present in
the export trie, not merely the local symbol table. The callback argument is a
function pointer, not a Boost/std::function object requiring reconstruction.
The encoded callback signature and invocation agree on four arguments:
chain reference, client refcon, message value, opaque message data; int result.
Registration takes callback/refcon and returns an integer ID. The registry starts
its ID counter at 1 in `BEE_Callback_Birth` (`0x333248`-`0x33324c`); the no-registry
branch of Insert returns -1 (`0x333760`). Removal searches the supplied ID and
erases only that entry; its examined result paths produce 0 or 1.
These are exact-build observations, not supported public SDK declarations.

**Actual client:** AfterFXLib `CEggApp::BirthSuites` calls the exported Insert
through its bound import stub at `0x769c18`, passing `CallbackFromBEE`
(`0x6fd7a4`) and its app pointer, and retains the returned ID at `0x769c20`.
`BEECancelCallbackEater` and `NewFauxCComp` also insert/remove their own callback
IDs. This establishes host use of an additive chain, rather than replacing the
single content-changed callback investigated earlier.

Registration is global and takes no BEE_Project/BEE_UndoContext pointer. Thus
this candidate does not need a private project pointer just to register. That
does not make callback payloads safe AEGP handles or solve snapshot context.

## Producer, message and UI-consumer links

The logger's message table is indexed by message-3 at BEE `0xfec608`.
Its entries are chained-fixup words: resolved them with LLVM dyld-info, not by
treating raw 64-bit words as pointers. The UI dispatcher uses a uint16 table
at AfterFXLib `0x18acd7c`: target = `0x8190d8 + 4 * table[message-3]`.
The following links were checked against the supplied bytes:

| Event | Message | Concrete BEE producer call | AfterFXLib UI case |
| --- | --- | --- | --- |
| Layer time | `0x3b` / LAYER_TIMESTUFF_CHANGED | SetLayerTime, `0x2a251c` | `0x81a430`; gets CLayer then invokes its UI update |
| Layer switches | `0x1b` / LAYER_FLAG_CHANGED | SetLayerSwitch, `0x2a3574` | `0x819e20`; ItemSettingsChanged |
| Layer reorder | `0x1a` / LAYER_REORDER | CompItem::ReorderLayer, `0x3380ec` | `0x819f90`; resolves current layer index |
| Selection | `0x57` / SELECTION_CHANGED | SetSelectionTask::Execute, `0x4ecb30` | `0x8198bc`; CComposition::SelectionChanged |
| Item time | `0x5f` / ITEM_TIME_CHANGED | SetItemTimeTask::Execute, `0x4ffca4` | `0x81987c`; item/view update |
| Project close | `0x5a` / PROJECT_CLOSED | Project::Close, `0x3a4004` | `0x8194a4`; project-related UI invalidation |

All six calls target BEE_Callback_UI_Submit (`0x3338f4`), which calls the chain
controller directly. The sampled producers gate on project field +0x2c being 1;
layer producers also have validity/error/suppression branches. No completeness
claim follows from those guarded paths. The LayerTime body writes the requested
time at `0x2a24ac` before its notification; it does not use the dirty byte as the
same-value gate from the rejected dirty-only signal. This is not a runtime
measurement of second edits, drags, Undo grouping or all scripting origins.

The native table also names Undo/Redo (`0x54/0x55`) and project new/opened
(`0x59/0x5b`). Their UI cases were mapped, but this step does not claim complete
producer coverage for them. ITEM_TIME_CHANGED is not by itself proof that every
playhead/active-composition change is covered. NEW_LAYER (`0x16`) and the unnamed
`0x74` map to the default FEE case here; names alone are not acceptance evidence.

## Critical safety distinction: a chain, not a passive observer list

Insert prepends a node. `BEE_FilterFunc::Execute` calls that node's callback;
it does **not** automatically continue after the callback returns. Native
`CallbackFromBEE` forwards through the supplied chain at `0x6fd7d0`, preserves a
nonzero downstream result, then invokes FEE_BEE_Callback only on success.
An FSTR callback that simply returns zero would suppress downstream AE behavior.

The controller constructs a stack iterator with vtable address point `0xfec5c8`.
The slot at address point +0x10 resolves to Iterator::Continue (`0x3353b0`),
confirmed by the dyld fixup at `0xfec5d8` and two independent native forwarders.
Continue advances to the next entry and returns its result. Neither a guessed
local Connect specialization nor an absolute call to private text is needed to
explain this route. A safe external implementation is still NOT ACCEPTED.

The future diagnostic callback must forward exactly once, preserve the result
and exception behavior, and never store chain or payload pointers beyond that
call. Selection/switch/item-time producers pass stack-backed data. Observation
should be bounded counters/invalidation, not payload dereferencing, a synchronous
AEGP project read, file I/O or recursive registration. Deactivation must leave
forwarding intact until safe removal of its own ID; no host callback replacement.

No lock was visible in the examined Insert/Remove/dispatch bodies. This is not
permission to use them concurrently. Thread affinity, reentrancy, exception
unwinding, in-flight callbacks and shutdown/removal remain explicit runtime gates.
Native ScQuietBEECallbacks deliberately swallows most messages in a temporary
scope, demonstrating that later filters can intercept a chain. Unconditional
full delivery must not be assumed. A successful callback is also not a transaction
commit barrier: SetLayerSwitch performs additional work after its notification.

## Verification and reproducibility

Input archive SHA-256 remains `2fb3acad42354fa7de409e1d8b14720cc6a4e546fbe5fad3cc5c38e3ec0fda7d`.
All three library hashes/UUIDs match the previous input baseline. Original archive
and read-only extracted files are retained outside Git. Only documentation and
compact metadata are committed; no Adobe binaries or full disassemblies published.

PASS: 25 complete symbol bodies / 7,472 contiguous four-byte positions matched
the mapped original bytes; seven independent BL immediate/target checks; two
exported registrar lookups; twelve selected message-name mappings and fifteen
UI switch-table destinations. The direct B/BL scan found 170 call sites to Submit
in BEE text; it is only a lead inventory, not a complete indirect call graph.
The .long fallback rows were byte-checked but are not all semantically decoded.
[Exact symbols, ranges, hashes and selected mappings](evidence/bee-callback-source-cfa8a1d.json).

Reproduce on these exact inputs with LLVM llvm-objdump 17.0.0:

```
llvm-objdump --macho --arch=arm64 --exports-trie BEE.dylib
llvm-objdump --macho --arch=arm64 --indirect-symbols AfterFXLib
llvm-objdump --macho --arch=arm64 --dyld-info BEE.dylib
llvm-objdump --macho --arch=arm64 --disassemble --dis-symname SYMBOL MODULE
```

Method references: LLVM llvm-objdump command guide and Apple's ARM64 ABI guide.
https://llvm.org/docs/CommandGuide/llvm-objdump.html
https://developer.apple.com/documentation/xcode/writing-arm64-code-for-apple-platforms
General ABI rules do not establish private host ownership/compatibility.

## Next decision, not another collector

Promote this callback-chain candidate to the next minimal native proof instead
of pursuing the unexported completion Connect as the primary route. First prove
pass-through registration/removal without altering AE behavior; then repeated
layer-time edits, native selection/reorder, script origin, Undo/Redo and idle.
Only event-driven pending state may trigger a fresh public-API read on the host
thread. No source event means no project scan; AEGP idle is dispatch, not polling.
Test cold/closed/reopened projects, downstream errors and callback interference.

SDK archive is not present in this runtime; no AEGP build/run is claimed. Existing
module inputs suffice for this static step; no more per-function Mac reports are
requested. If transparent forwarding/lifecycle or required origins fail, reject
or narrow the candidate rather than silently weakening SYNC-001.

Documentation/evidence consistency checks apply under rules section 9. Product
build/runtime regression: N/A for this documentation-only change. Any incidental
CI result is separate. No package handoff, runtime fix or #3 closure is claimed.
**Native subscription/AE compatibility/SYNC-001 remain NOT RUN/BLOCKED.**
