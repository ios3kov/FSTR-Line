# Implemented native chain observer core — 2026-09-30

Run `CHAIN-CORE-20260930-01`; baseline `516500997b48d4e4dd523156290165bc05b21214`.
Branch `integration/host-safety-notifications`, PR #2 Draft/unmerged; phase 0,
0/5 accepted. Main rules reread, blob `701a8c1ae3acb4dbfe1d7eda94acbf8095b88608`.
Scope: **native callback implementation and owned executable controls**, not
an AEGP plugin or an actual Adobe registration. No further collector or LLDB work.

## Required acceptance for this increment

Before a host integration, the implemented callback must forward exactly once,
retain all argument bits and result/error behavior, never retain or dereference
message data, record repeated invocations, and remain transparent when disabled.
Exercise normal/error/exception, unknown messages, nested callbacks and an
in-flight disable in compiled C++. Run optimized and ASan/UBSan controls,
check Apple arm64 calling-convention lowering, and keep AE acceptance separate.
The owned fixture must remove only its registration at a known quiescent
boundary. An in-flight counter alone must not authorize host removal/unload.
The current workflows must execute these new tests before any package handoff;
there is **no package handoff** in this step.

## Implementation, not another source search

`research/ae-notifications/chain-probe/chain_abi.hpp` defines only the inspected
binary-boundary scalar/function signatures. `continue_chain` loads the vptr,
loads the Continue slot at +0x10, and forwards chain/message/payload. It does not
reconstruct a vendor class or call a private absolute address. The precondition
is a valid live chain from a separately verified binding. Returning zero on an
invalid chain would swallow host work, so this is not advertised as corruption
recovery. A real host binder is deliberately absent until its gates are met.

`observer.hpp` implements the actual callback and fixed atomic counters. New
observations are opt-in; both disabled recording and null refcon still forward.
Errors, including INT_MIN/INT_MAX, are returned unchanged. A downstream C++
exception is rethrown without translation; RAII releases only the observer's
in-flight counter. No exception is converted into successful delivery.
Messages outside the 128-bin range use an unknown bin while preserving their
original numeric argument. Overflow invalidates counter evidence. The overflow
branch has not been forced by this test fixture.

Disabling is **logical deactivation only**. Calls already captured finish their
accounting. No destructor calls BEE Remove, deletes a refcon, or unloads code.
Snapshots during activity are diagnostics, not coherent transaction records.
No SDK call, timer, self-wakeup, payload access, project read or registry write
exists in the implemented observer. Thus it cannot yet synchronize the panel.

## Basis for the binary-boundary code

The supplied three-module archive is still
`2fb3acad42354fa7de409e1d8b14720cc6a4e546fbe5fad3cc5c38e3ec0fda7d`.
Its four-entry membership and all three module hashes were rechecked against
its manifest. Read-only extracted copies remain outside the repository.
The existing [source record](BEE-CALLBACK-SOURCE-2026-09-30.md) establishes the
four callback arguments and +0x10 continuation slot. Insert/Remove and the
AfterFXLib `CallbackFromBEE` forwarder were reread from those exact binaries:
caller x0=chain, x1=client, w2=message, x3=data; continuation receives x0=chain,
w1=message, x2=data. Remove's found path sets result 1; not-found sets 0.
No call to those Adobe functions was made.

The compiler-emitted Apple arm64 shim is checked for two pointer loads and an
indirect tail branch, with no writes to argument registers, stack stores or
helper calls. This supports the specified **code generation**, not runtime
private-ABI compatibility. References:

- https://developer.apple.com/documentation/xcode/writing-arm64-code-for-apple-platforms
- https://itanium-cxx-abi.github.io/cxx-abi/abi.html#vtable

The latter explicitly defers platform-specific authority to platform vendors.
It does not turn a private host ABI into an SDK-supported interface.

## Executed controls and evidence boundaries

`chain_probe_control.cpp` owns its registry, iterator table, process and data.
Its registry is serialized and rejects mutation while a dispatch is active.
That is a fixture rule, **not an assumption that AE has the same synchronization**.
It executes the new `Observer::callback`, not a mock of the observer.

Ten scenario groups run in each optimized and sanitized executable:

1. Repeated numeric layer-time messages and unchanged 0/positive/negative/extreme results.
2. Disabled/enabled/disabled capture and null refcon, with uninterrupted forwarding.
3. Fixture registration/removal by own ID, retaining another subscriber.
4. Rethrown exception pointer identity and balanced in-flight count.
5. Nested dispatch: both invocations continue, depth reaches two and returns to zero.
6. Unknown numeric messages and PROT_NONE payload: no payload dereference.
7. Ten thousand normal invocations without a C++ heap allocation in that path.
8. Rendezvous-controlled disable during a live callback; removal only after joining.
9. Four independent fixture chains sharing atomic observer counters (4,000 callbacks).
10. All 128 bins and an unchanged overflow indicator.

Local Linux: optimized PASS, ASan/UBSan PASS, Apple arm64 assembly check PASS;
three Python test methods, not three AE tests. LeakSanitizer is disabled; no leak
or timing/CPU claim is made. The allocation control checks ordinary C++ new/new[]
in the exercised callback path, not all possible host allocations. Concurrent
fixtures validate the observer counters, not concurrent BEE registry mutation.
Exact local input/tool/log identities: [evidence](evidence/chain-core-5165009.json).

The local workspace is a source subset, not a full Git checkout: cloning failed
because GitHub DNS was unavailable. Existing branch-wide CI is left unchanged
and will run these controls on Linux/macOS. Its exact-containing-commit results
are recorded separately in PR #2; earlier successes are not substituted.
Historical #3 failures are not retried or claimed fixed by this increment.

## Next executable gate and missing SDK

The matching SDK is still absent from mounted conversation files. The Files
discovery did not expose a file-read/materialize tool, so no unmounted SDK was
read. No replacement SDK declarations were invented. The next implementation
is the AEGP entry point and exact-loaded-image binding using the actual headers,
with disabled startup and explicit controlled activation. SDK availability alone
does not resolve host thread/quiescence or exception/lifecycle acceptance.

Require the disposable real-AE gate without LLDB: first/repeated native edits,
script edits, selection/reorder, Undo/Redo, closed/switched projects, deactivation
and removal with ordinary AE behavior preserved. The event-to-main-thread
pending/AEGP-read path is also not implemented by this counter-only core.

**Implemented/compiled: native observer core. AEGP build/load, actual BEE
registration/removal, safe host lifecycle, full SYNC-001: NOT RUN/BLOCKED.**
No Adobe binary, SDK, production change, main change, merge, deploy or release.
