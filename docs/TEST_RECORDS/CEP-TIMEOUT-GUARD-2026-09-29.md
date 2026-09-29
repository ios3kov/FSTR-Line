# CEP timeout host-call guard — 2026-09-29

Run: `CEP-GUARD-20260929-01`. Baseline:
`99d40f983f061d4357aa14c99985132096ab161d`.
Environment: macOS arm64, Node 24.12.0, npm 11.6.2. Target runtime:
AE 25.6.0.101 / CEP 12. Actual AE reproduction: NOT RUN.

## Requirement and baseline

The panel must not submit a second call through an adapter while an earlier
host invocation may still be running. Promise timeout is not host cancellation.
The baseline released `operationTail` on timeout, allowing another evalScript
dispatch. Three new regression tests reproduced that behavior before the fix:
6 existing tests PASS / 3 new tests FAIL in `cep-recovery.test.ts`.

The tests exercise the actual adapter with a controlled callback transport.
They prove dispatch ordering, not Adobe's native runtime behavior.

## Change and acceptance

- Keep a per-invocation pending token after timeout or synchronous dispatch
  exception. Clear it only on that invocation's actual callback.
- Refuse queued/later snapshot, diagnostics and command operations with
  `HOST_CALL_PENDING` before they are dispatched.
- A refused, unsent command must not set uncertain-mutation state.
- A late callback must not resolve the expired read; a duplicate callback must
  not unlock a different invocation.
- A late completed command permits later reads, but never clears the existing
  uncertain-write lock. No command is replayed.
- Recovery if no callback ever arrives requires a verified new host session.
  Recreating an adapter or reloading a panel is not cancellation evidence.
- `readNotificationSnapshot()` retains its Promise until host completion even
  when the normal UI-facing read has timed out. The delivery controller owns
  its own deadline and keeps its single-flight guard. A combined delivery/CEP
  harness exercises late completion and explicit recovery.

Automated acceptance: three new reproduction tests now pass, together with
the existing recovery/serialization suite. Updated runtime harness retains the
uncertain-write assertion and adds blocked-read verification before delivering
the old command callback. No assertion was removed to admit overlapping calls.

Planned gates: `npm test`, `npm run check:cep`, runtime tests, research tests,
package verification on a clean commit, code scanner and CI for the pushed
head. Dirty packages cannot pass the package verifier; build the committed
candidate for that gate. Record final results after the implementation commit.

Development results: 68 TypeScript tests PASS, CEP build/host syntax PASS,
32 selected runtime tests PASS (package checks deferred to clean build),
91 research tests PASS. Static code scanner completed without omissions and
returned exit 1 for three eval heuristics: the named `CEPAdapter.eval` wrapper,
its generated client copy, and the existing vendor JSON2 guarded parsing code
in the generated host. These are reviewed existing paths, not a new dynamic
code execution interface. This is not a whole-product security acceptance.

## Limits

The guard is scoped to one adapter instance and cannot coordinate other
extensions, a newly created adapter or another CEP process. Current client
entry point owns one adapter. Cross-panel/native session recovery remains a
producer integration requirement. `NotificationDelivery.read()` requires the
new `readNotificationSnapshot()` method; the ordinary UI-facing `readSnapshot()`
still rejects at its deadline and does not supply that contract.

Real AE timeout/recovery, runtime identity and playback impact: NOT RUN for this
change. No new package is delivered for installation. The source gate remains
open; see `NATIVE-SUBSCRIPTION-ABI-2026-09-29.md`.

Source: [Adobe CEP 12 Cookbook — invoking scripts](https://github.com/Adobe-CEP/CEP-Resources/blob/master/CEP_12.x/Documentation/CEP%2012%20HTML%20Extension%20Cookbook.md#invoke-point-products-scripts-from-html-extension).
The documented API uses a result callback; a local JavaScript timer does not
cancel that host call. Both ExtendScript and CEP event dispatch use the host
main thread. The fail-closed guard is a project policy, not an Adobe guarantee
of transaction semantics.
