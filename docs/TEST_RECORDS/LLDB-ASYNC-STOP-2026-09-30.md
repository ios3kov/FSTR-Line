# Asynchronous stop confirmation and target liveness — 2026-09-30

Baseline: `678c89d7b6aa4a1850c4d46c0ea85e7655d27968`. Phase 0; 0/5 accepted.
Main rules blob: `701a8c1ae3acb4dbfe1d7eda94acbf8095b88608`.
Scope: research controller/logger, owned-process smoke and tests. No Adobe process,
private invocation, production panel, queue collector, project or preferences change.
Main, merge, deploy and release are outside this increment.

## Acceptance fixed before implementation

Preserve the retained Stop timeout and target-death anomaly. Remove synchronous
`SBProcess.Stop()` from normal and recovery shutdown without weakening stop/detach,
exit-code or timeout acceptance. Require observed stopped state before detach;
reject unconfirmed stop, terminal states and failed detach. A failed operation is
not retried until green. Verify late callbacks cannot request automatic resume
once shutdown mode is set. The test target must demonstrably progress after the
debugger has exited, before test cleanup can resume/terminate it.

Required checks: deterministic controller/error/abort tests, actual logger tests,
real owned-child liveness controls, Python syntax and source review. Full branch
build/regression/package/clean-source CI and the existing five controller/IPC plus
five packaged-parent real LLDB captures in each macOS workflow remain mandatory.
No deadline is increased and no failing gate is waived. Runtime AE and shipping
SYNC-001 remain NOT RUN; this is not a user diagnostic handoff.

## Retained baseline, not a new native reproduction

Artifact `11119655143` from PR run `36761397239`, job `110044576067`, was re-read:
archive SHA-256 `dc5a888e7dd7bfd77c7c958744245fbdb927a47531ef8b828b0dfe4ad9007ae0`.
ZIP CRC, summary sidecars and every stored text hash were checked. Original bytes
were not edited. Source/runtime-kit identity is the baseline commit, Build ID
`fstr-final-matrix-678c89d7b6aa`, runtime ZIP SHA-256
`854c964bf7183410f4f9720e4b6c401682fbd9da771cf572e94551a02e27a571`.

- `run-dsmzyz48`: FAIL/TimeoutExpired. Last marker `stop-begin`, no `stop-end`,
  detach or result. Source places synchronous Stop at that boundary. This localizes
  that occurrence, not every old timeout and not the native lock/callback cause.
- `run-w58jg1hy`: recorded PASS/13 hits/LLDB exit 0, but the fixture was already
  dead with exit -9 before cleanup (`actions: []`). The old smoke lacked independent
  post-detach target progress acceptance. Do not treat this run as target-safety PASS.
- `run-kh5ykbpe`: recorded PASS. No new interpretation of unseen runtime behavior.

The old 15-second timeout is not reproduced on this Linux host. The retained
macOS failure is the baseline; simulated API tests are not a substitute for it.

## Reason for the candidate change

Primary upstream references inspected 2026-09-30:

- https://lldb.llvm.org/cpp_reference/SBProcess_8cpp_source.html
  `SBProcess::Stop` holds the target API mutex while calling `Halt`;
  `SendAsyncInterrupt` forwards the interrupt request without that surrounding wait.
- https://lldb.llvm.org/cpp_reference/Process_8cpp_source.html
  `Process::SendAsyncInterrupt` posts an interrupt event; this is a request,
  not a completion receipt.
- https://lldb.llvm.org/python_api/lldb.SBProcess.html
  Python binding includes `SendAsyncInterrupt`, `GetState`, and `Detach`.

These upstream sources motivate avoiding a synchronous halt while callbacks are
active. They do not establish the exact implementation or root cause in Apple's
LLDB 1700.0.9.502. The candidate must pass real Apple-tool tests independently.
Simply setting SetAsync(True) around Stop would not remove that blocking API.

## Changed shutdown contract

The controller leaves execution asynchronous, marks the logger for teardown, sends
at most one asynchronous interrupt when running/stepping, and waits up to five
seconds for observed `eStateStopped`. An already stopped target needs no interrupt.
Unexpected/terminal state, interruption failure and missed deadline remain FAIL;
there is no synchronous Stop/Detach fallback when stop is unconfirmed.

The five-second inner deadline is smaller than the existing parent exit deadline.
It bounds the Python wait, not the internals of every native SB API call; the
separate parent watchdog/cleanup and zero-exit acceptance remain essential.
The bounded state check observes the debugger's process state, not AE project
changes; it is not a polling-based implementation of SYNC-001.

After stop confirmation, `Detach(False)` explicitly requests normal resumption.
The capture stream is closed after detach, not while a running callback can still
use it. The logger's teardown flag makes subsequent callbacks pause without reading
SB objects or claiming another notification. It is not by itself a quiescence proof.
Early setup errors use the same stop/teardown path. Failed detach is not repeated;
FAIL and unconfirmed detach survive into the parent's separate acceptance record.
Target retention until the dedicated debugger exits remains unchanged.

## Independent owned-fixture liveness

The native smoke fixture now writes an eight-byte increasing counter itself.
The smoke requires advancement before attach and again after LLDB exits, without
sending SIGCONT or any other signal to make the latter check pass. A dead, frozen,
malformed or missing counter fails. The test checks the child again before cleanup.
The recorded before/after values and oracle type are included in its evidence.

The C++ fixture is finite, its counter stays in the unique owned test directory,
and cleanup retains its existing Popen-only ownership restriction. The helper
never discovers or signals an AE/user process. This is a liveness observation for
the checked interval, not proof of indefinite survival or correct project state.

## Local checks and limits

The runtime sources were obtained from the retained verified exact CI ZIP, and
baseline Git blob IDs were checked for controller, logger and test files. GitHub
DNS still prevents a full local checkout. This is a source-subset test, not a clean
build of the full repository; the exact containing commit's CI supplies that gate.

29 local tests PASS: 15 added checks and 14 existing checks, including adjusted
shutdown-model fixtures. New cases cover running/stepping/already-stopped,
terminal/error/timeout, no blocking fallback, abort, early setup failure, failed
detach, late callbacks and owned-process dead/stopped/progress controls. Python AST
checks PASS. Full macOS and branch checks are recorded in PR #2 and CI artifacts
for the exact containing commit; previous-commit successes do not substitute.

Issue #3 stays OPEN pending native evidence and review; the internal cause of the
old halt stall and target-death anomaly is not claimed. No diagnostic package is
handed to the user by this record. Next: inspect exact-commit native results and
liveness evidence; any failure stops acceptance. Then resume the already prepared
offline context/table collection, without repeating the retained 19-body report.
