# Retained LLDB shutdown diagnostics — 2026-09-30

Run: `LLDB-DIAGNOSTICS-20260930-01`. Baseline:
`44a3556f80d962d6f826c1da2728c5dd8d569fc6`. Phase 0, 0/5 accepted.
Rules reviewed from main, blob `701a8c1ae3acb4dbfe1d7eda94acbf8095b88608`.
Scope: issue #3, research controller diagnostics and owned-process QA only.
No product/queue collector changes, private Adobe calls, installation, AE launch,
user project access, system security changes, merge, deployment or release.

## Baseline and acceptance defined before editing

Baseline mac-research push job 110006868942 failed waiting for LLDB exit after
15 seconds. The other macOS run passed. Earlier issue #3 records the same failure
on 6c22da4. Neither PASS nor a retry establishes a cause or a fix. The old smoke
removed its TemporaryDirectory on exception, losing the stage, acknowledgements,
trace and debugger log. Preserve those failures and their CI URLs in issue #3.

Required: exact source/kit identity; unique, bounded and redacted evidence on
success and failure; progress before/after blocking shutdown operations; bounded
cleanup of only owned children; deterministic diagnostics controls; full existing
CI and five separate exact-kit macOS runs, stopping at the first failure.
No longer deadline, retry-to-green loop, relaxed assertion or guessed native fix.
Real AE and SYNC-001 are NOT RUN, not substituted by these tests.

## Changes

- Optional `diagnosticStages` in the generated test plan records progress around
  Stop, logger closure, Detach, result writing, recovery and DeleteTarget. The
  records use the existing acknowledgement file, with distinct kind and monotonic
  timestamps. Logging errors are bounded and do not prevent detach attempts.
- The smoke drains LLDB output while retaining at most 256 KiB. Evidence copies
  only six named regular files, with a 256 KiB input limit each. Symlinks and FIFOs
  are refused; missing/truncated data stays explicit. Fixture/home paths are
  redacted before JSON encoding; hashes describe the stored redacted bytes.
- Every started attempt saves summary.json and SHA256.txt before its temporary
  directory is removed. Parent FAIL remains FAIL even if result.json says PASS
  before a subsequent debugger exit timeout. Source commit, exact kit digest,
  Build ID and per-child cleanup results accompany the captured text.
- Cleanup is limited to Popen children created by this smoke. A stopped owned
  fixture receives SIGCONT after SIGTERM so it can exit; bounded kill/wait fallback
  is recorded. This helper is not shipped and accepts no user-supplied PID.
- CI runs five separate captures and stops at the first FAIL, retaining diagnostics
  with an always-upload step. Each workflow/run/attempt has a separate artifact.
  The existing smoke assertions and 10/5/15-second protocol/exit deadlines remain.

No Stop/Detach ordering or algorithm was changed in this diagnostic increment.
Progress logging changes timing and is not an uninstrumented latency measurement.
A last begin record identifies the pending operation, not necessarily its internal
root cause. Abrupt machine/job termination or output-disk failure can still prevent
an evidence write; no unconditional persistence claim is made.

## Executed local verification

Linux, Python 3: 13 new tests PASS. These cover unique evidence, retained FAIL,
missing files, bounded prefixes/live log drainage, path redaction, symlink/FIFO
refusal, stopped-child cleanup while preserving another owned child, explicit
cleanup failure, bounded kill fallback, opt-in stages, logging I/O failure, ordered
successful fake-SB shutdown and fake Stop failure with recovery. The fake-SB tests
are not actual LLDB or AE. Syntax parsing PASS.

A full clone was attempted and failed because github.com DNS is unavailable in
this container. Local tests therefore use a source subset. The unchanged runtime
support files were extracted from the prior CI artifact and matched against Git
blob identities; controller baseline blob is
`93f29fe9ed619a5e84e79d0be9ba29d7bdd98711`. Uploaded changed code is verified
against the exact locally tested bytes. Full build/package/regression and actual
macOS LLDB results belong to the containing commit's CI; record them in PR #2 and
issue #3, never substitute the baseline's result.

Reproduce: `python3 -B -m unittest discover -s tests/research -p test_smoke_evidence.py -v`.
macOS: build the exact clean runtime kit using the existing packaging script,
then `python3 -B tests/research/mac_runtime_attach_smoke.py --runs 5`.

## Next gate

Inspect retained actual macOS failure stages before changing shutdown behavior.
If all five runs pass, root cause remains unproven; do not close #3 by inference.
Queue ordering/thread, UI-clone association, registration/lifetime and shipping
notification delivery remain open as recorded in QUEUE-ORDER-CLONE-2026-09-30.md.
Tool references consulted (not an AE safety guarantee):
https://lldb.llvm.org/python_api/lldb.SBProcess.html and
https://lldb.llvm.org/use/tutorials/breakpoint-triggered-scripts.html .
