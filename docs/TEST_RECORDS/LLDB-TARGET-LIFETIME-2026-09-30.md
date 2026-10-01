# LLDB target lifetime follow-up — 2026-09-30

Run: `LLDB-TARGET-LIFETIME-20260930-01`. Baseline:
`be1875422b61d50b0b166b5a09dce6415cd20b03`; tree
`f8c122137aa5ec4376fd96213f3c3b9491c82921`. Phase 0, 0/5 accepted.
Rules main blob `701a8c1ae3acb4dbfe1d7eda94acbf8095b88608` unchanged.
Scope: isolated research debugger lifetime, not Adobe notification delivery.

## New evidence: crash, not the old timeout

The diagnostic increment's two macOS workflows each failed on their first
capture, stopping the five-run series. Both Linux Integration gates passed.
No workflow was rerun to replace these failures.

| Evidence | PR | Push |
| --- | --- | --- |
| Workflow run | 36752148772 | 36752143694 |
| Diagnostic artifact | 11114623581 | 11115535218 |
| Owned run | run-2jqjmln5 | run-fu45el1s |
| ZIP SHA-256 | `7aa2a5a36955b83f9e71f098aaa1405ba2e1198ed00a033c9435fc9f5caa7330` | `c447d5c8fbac76cf6f33d1eb44c69223af8fa5679a1ef474592d7218c8871e3d` |

CI: https://github.com/ios3kov/FSTR-Line/actions/runs/36752148772 and
https://github.com/ios3kov/FSTR-Line/actions/runs/36752143694 .
Both downloaded ZIPs and their summary.json sidecars were hash-verified.
Both identify the clean runtime kit at baseline, Build ID
`fstr-final-matrix-be1875422b61`, kit SHA-256
`9905683e4a04c42541043f09712c25a89c120f9979d8d543bbf0f3fa0919b9a1`.
Environment: macOS 15.7.9 arm64, Apple LLDB 1700.0.9.502, Python 3.14.7.
No Adobe code or user project was loaded by these owned-fixture runs.

Both acknowledgement logs record Stop and Detach returning, result writing,
DeleteTarget returning and controller-return. The embedded result is
PASS/detached=true, but the LLDB process exits with **-11 (SIGSEGV)**. Its stack
contains Process::GetTarget, Process::HandleProcessStateChangedEvent,
Debugger::HandleProcessEvent and Debugger::DefaultEventHandler. The parent
correctly keeps FAIL because a zero debugger exit code is now mandatory.
Both owned children were reaped; the retained LLDB logs are not truncated.

This locates a post-controller-return crash in event processing after explicit
target deletion. It is not a reproduction or root-cause proof of the historical
15-second timeout. Issue #3 remains open. Earlier smoke code ignored the exit
code; this exposes a possible false-PASS path, not proof that previous PASS runs
actually crashed.

## Bounded hypothesis and change

Premature destruction of a target still referenced by debugger events is a
plausible cause of this crash signature. Upstream LLDB source shows
SBDebugger::DeleteTarget removing and destroying the target immediately, while
Debugger::Clear stops its event-handler thread before destroying targets.
StopEventHandlerThread joins that thread. Sources consulted 2026-09-30:

- https://lldb.llvm.org/cpp_reference/SBDebugger_8cpp_source.html — DeleteTarget.
- https://lldb.llvm.org/cpp_reference/Debugger_8cpp_source.html — Clear and StopEventHandlerThread.

These are upstream sources, not a claim that Apple's binary is identical.
They motivate the change; actual Apple LLDB runs must validate the result.

The controller no longer explicitly calls DeleteTarget inside its Python
callback. The dedicated debugger retains that target until normal batch-process
teardown. Stop, Detach, return-code checking, log completeness and child cleanup
remain mandatory. A single-use guard refuses a second capture in that module,
so this is not an accumulating target cache. Existing runtime_probe launches a
fresh LLDB batch process for each observer session. No arbitrary process kill,
extra sleeps, timeout increase or polling-based notification source is added.

The latest code still may fail in Stop/Detach or debugger exit; retaining a target
is not a guarantee of quiescence of Adobe callbacks. This is a research-only
lifetime change. Rollback is a normal revert, not a force push.

## Acceptance and executed local checks

Required before claiming the tested crash path corrected: deterministic contract
regression, exact clean kit, five separate successful owned-process captures in
each macOS push/PR workflow, and all existing build/package/regression gates.
Every capture must show detach, controller return, zero LLDB exit, complete
bounded logs and reaped children. Stop at the first failure; no retry-to-green.

Local Linux source subset: **14 tests PASS**, including target retention on
success and Stop-error recovery, reentry refusal before target creation, and the
13 diagnostics/cleanup scenarios from the prior record. Replaying the new tests
against the be18754 controller gives two failures and one error for the changed
ownership/single-use contract. These model tests are not the actual Mac crash;
the two baseline CI archives above supply the actual crash evidence.
Controller/test bytes match uploaded Git blob hashes. Full local clone/build is
unavailable because GitHub DNS failed. The exact containing commit's full CI and
macOS evidence will be recorded separately in PR #2 and issue #3; no ancestor's
PASS substitutes for that verification. No new user artifact is handed off.

## Remaining gates

Keep the original timeout history and both new crash reports. Even a successful
new series would support only this tested debugger path, not a full resolution
of #3 or real-AE shutdown safety. The ordinary runtime_probe parent also needs
an explicit nonzero-exit rejection audit; its current acceptance of result.json
alone must not be treated as successful debugger termination. It is unchanged
in this lifetime increment and remains a prerequisite for a new real-AE handoff.

SYNC-001, UI/clone mapping, safe subscription/ownership, actual source coverage,
post-commit semantics and uninstrumented performance remain BLOCKED/NOT RUN.
Main, production code, queue collector and user projects are unchanged.
