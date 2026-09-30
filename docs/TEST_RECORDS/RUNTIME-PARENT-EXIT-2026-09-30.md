# Runtime parent exit acceptance — 2026-09-30

Baseline: `3daca55bdc72b80a9d11591db416ebd583cbaaa5`. Phase 0; 0/5 phases accepted.
Rules reviewed from main: blob `701a8c1ae3acb4dbfe1d7eda94acbf8095b88608`.
Scope: the research `runtime_probe.py` parent, its regression tests and exact-kit
macOS CI. No production panel, SDK/private ABI, queue collector, user project,
installation, merge, deploy or release changes. Issue #3 remains open.

## Acceptance and baseline

Required for this increment: reproduce the parent's false acceptance, require
both controller evidence and a normal debugger exit, cover ready/capture/exit
failure and cancellation, preserve diagnostics, and avoid signalling an AE PID.
Unit/owned-child controls and actual-source regression run locally; full branch
regression/build/package and five real packaged-parent LLDB captures per push/PR
run are required in CI. No real-AE handoff is made by this increment.

Three new tests on the exact baseline source failed (four failing subcases):

- controller PASS plus child exit 7 or -11 was accepted;
- shutdown timed out, cleanup yielded exit 0, and controller PASS was accepted;
- failure while waiting for ready bypassed the parent's cleanup block.

These reproduce defects in the actual parent function with a controlled child
interface. They do not reproduce the old native 15-second hang or prove its cause.
Baseline runtime_probe blob: `01004297db8354ceb030f88c96d9a153cd72e2fa`.

## Change and failure semantics

The protected lifecycle now starts before Popen/ready, not after ready. Wait
bounds are validated before launch. The parent requests abort on errors and
settles only its own Popen child. A shutdown timeout is sticky: TERM/KILL cleanup
cannot turn it into PASS even when the final exit code is zero. Cleanup waits are
bounded; normal configured deadlines were not increased. The host PID in the
plan is never passed to a signal, kill, termination or restart operation.

Acceptance requires all of: no session exception, finish sent, debugger reaped,
integer exit code 0, no shutdown timeout/forced cleanup/cleanup error, and a
bounded regular controller JSON object with status PASS, stage complete,
`detached is True` and the exact integer target PID. Missing, malformed,
oversized, symlinked, wrong-PID or truthy-but-not-boolean results are rejected.

The original `result.json` is never rewritten. A separate, exclusive-created
`observer-parent.json` binds the decision to the run ID, exact plan hash and
controller result hash. Successful matrix archives now include this record.
Rejected sessions retain their existing workspace/log/controller evidence; no
old PASS is relabelled, deleted or used as proof of a new run. Popen/ready/capture
exceptions are re-raised after cleanup and the parent record, rather than masked
by a later controller PASS.

Automatic resume additionally needs a matching parent ledger with normal exit
and `resumeEligible: true`. Only cleanly detached controller-aborted sessions
following KeyboardInterrupt/EOFError qualify; normal prefix/PID/breakpoint checks
still apply. Legacy result-only, crashed, timed-out and changed evidence is not
automatically resumed. Historical files are left intact. The existing positive
resume fixture was extended with this evidence; a negative legacy assertion was
added, not removed.

Quoted module paths are passed to LLDB command imports. The actual Mac parent
smoke deliberately extracts its unchanged ZIP into a path containing spaces.

## Verification

Local environment: Linux, Python 3.13.5. GitHub clone DNS failed. Local files are
an exact-blob-verified source subset, not a full checkout. The unchanged
runtime_protocol and collect_app dependencies match baseline blobs
`bd7dcb5eb93989ba4d0bb21ee09fa540a05a644b` and
`2d92e90c8cc11b101adefb2ebc0b41408b9b8159`.

- 23 tests PASS: 15 new parent/cleanup/resume tests plus eight existing final
  matrix tests, including the strengthened resume fixture.
- Real owned Python children exercise file IPC and actual zero/nonzero/signal
  exits, ready timeout, a hanging child handling TERM with exit 0, and escalation
  for a TERM-ignoring child. No LLDB or Adobe application runs in these controls.
- Baseline failure, positive path, strict JSON/PID checks, sticky timeout,
  unchanged controller output, original exception preservation, existing-session
  refusal, cleanup failure and invalid wait bounds are covered.
- Python AST and whitespace checks PASS.
- Actual macOS/LLDB is NOT RUN locally. `mac_runtime_parent_smoke.py --runs 5`
  uses the exact clean CI ZIP and real native target/debugger. Only snapshot/UI
  actions are replaced; launch, real IPC, controller, exit/result gate and
  cleanup are the packaged implementation. It verifies target survival after
  detach and retains bounded diagnostics on success/failure. Stop at first FAIL;
  no retry-to-green and no relaxed timeout or assertion.
- Full branch CI results and exact kit hashes belong to the containing commit
  and are recorded in PR #2, not borrowed from baseline's 10 successful captures.

Reproduce the local subset tests:

```sh
python3 -B -m unittest discover -s tests/research -p test_runtime_parent_exit.py -v
python3 -B -m unittest discover -s tests/research -p test_final_matrix.py -v
```

Primary reference: Python subprocess documentation,
https://docs.python.org/3/library/subprocess.html#subprocess.Popen.wait and
https://docs.python.org/3/library/subprocess.html#subprocess.Popen.returncode
(consulted 2026-09-30). Child termination and result-file content are separate
observations; a TimeoutExpired does not certify normal completion.

## Remaining limits

No claim of real-AE observer safety, production notification delivery, original
hang resolution, performance gain or phase acceptance. Forced debugger shutdown
does not prove the host is detached or responsive; it is a rejected run and the
host is never forcibly terminated. Repeated interruption, process/OS crash or
unwritable storage can prevent final diagnostics; absence is not success.

This is the exit/cleanup boundary, not a redesign of matrix scenario acceptance,
project lifetime/PID reuse, all other launchers, or snapshot/IPC validation. Those
existing scopes are not certified by this change. Queue callback thread,
UI/clone association, context acquisition, external subscription/emitter and
callback quiescence remain unproven. SYNC-001 stays BLOCKED/NOT RUN.
