# Offline matrix observer integrity — 2026-09-30

Test run: `MATRIX-INTEGRITY-20260930`. Baseline:
`df13e1b47d694f8672e28ffaf41b9df01eb335b6`, working branch
`integration/host-safety-notifications`, Draft PR #2. Phase 0, 0/5 accepted.
Rules rechecked from main, blob `701a8c1ae3acb4dbfe1d7eda94acbf8095b88608`.

## Scope and acceptance established before implementation

The downstream offline analyzer must not discard the parent exit gate added by
df13e1b. Require normal parent exit plus matching controller/result and complete
trace lifecycle before crediting a research window. Retain raw observations and
original archives on failure. Check missing/abnormal/legacy evidence, result hash
binding, capture identity/order/counts, resumed sessions and semantic overclaims.
ZIP/JSON processing must be bounded and must not execute or extract input files.

Required checks: baseline reproduction; actual-source unit and CLI checks;
existing matrix regression; offline replay of retained exact-identity macOS
artifacts; Python syntax and patch whitespace; full branch CI on the exact new
commit. Existing Linux/macOS workflows remain mandatory and unmodified. No
retry-to-green, deadline relaxation or removal of an existing safety assertion.

This is an analyzer-only increment. No Adobe process, debugger attach, private
ABI, SDK, user project, preference, runtime launcher/controller, queue collector,
production panel, installation, merge, deploy or release is changed. Real-AE
execution and full launch-chain acceptance remain NOT RUN. Issue #3 stays open.

## Baseline reproduced

The baseline analyzer blob was verified as
`12acac8909e09f9de70b55b59d95f1a6cc85cf70`; the existing matrix-test blob as
`27dfab2eec1df0942e2de45dc46273272d772ad3` before editing.

Three tests failed in four subcases using the actual baseline analyzer:

- debugger exit 7 or -11 with summary/controller PASS still yielded runtime PASS;
- an absent observer-parent record was ignored;
- an empty pre-restart trace retained PASS and the unconditional native-path claim.

These are reproducible analyzer defects, not new crashes observed in After Effects.
The old algorithm also inferred a post-commit PARTIAL from any nonempty snapshot,
and restart/reopen from a pidChanged flag. Neither supplies the missing state or
project-identity proof. Absent action windows must not be reported as proven gaps.

## Change and compatibility

`analyze_runtime_matrix.py` now emits schemaVersion **2**. The original summary's
status is retained as `reportedRuntimeStatus`. The computed `runtimeStatus` is
PASS only for validated supplied observer lifecycle records; this is expressly
not complete matrix coverage, genuine host provenance or product acceptance.
CLI returns 2 for a parsed-but-blocked archive instead of unconditional zero.
Raw session windows and counters remain available for historical investigation.
Invalid containers/JSON fail rather than being repaired or credited.

Per-session validation checks exact booleans/types for clean exit, no timeout or
forced termination, reaped debugger, no cleanup/session errors; matching raw
controller-result SHA-256; controller stage/status/detach/PID; capture start/end,
run ID, contiguous record sequence, monotonic timestamps, hit count and lifecycle
markers. Capture errors/limits, contradictory claims and ambiguous windows block
acceptance. Result hashes establish internal linkage, not authenticity.

Supported layouts are the existing two-session capture and the existing
partial/resume/post-restart capture. A partial session must be a clean explicit
user abort with resumeEligible, not a crash treated as a cancellation. Its
completed windows remain in their own clock domain. Reused run IDs, duplicate
completed windows and mismatched pre-restart PIDs are rejected. Original partial
session evidence retains its `pre-restart` label and is correlated accordingly.

Script-origin window credit additionally needs the matching successful script
result and no conflicting step-blocked row. Native-path credit needs an actual
native-window candidate hit, not a constant OBSERVED. These are research window
correlations, not comprehensive source coverage or shipping notifications.

`postCommitSemantics`, `activeCompSwitch`, `restartReopen` and `otherPluginOrigin`
remain UNPROVEN because this analyzer does not implement the independent semantic
or provenance oracles. PID correlation is exposed separately as `restartProcess`;
raw active-comp candidate counts and snapshot availability are retained. This
more conservative interpretation does not rewrite any historical test record.
`SYNC-001` is always NOT RUN.

The analyzer accepts at most 64 members, 32 MiB per member, 128 MiB total,
12,000 JSONL rows per stream and 128 complete windows. Duplicate ZIP names,
unsafe names, symlink members, encryption, duplicate JSON keys, invalid UTF-8
and incomplete JSONL tails are refused. Input archives are never extracted.
Larger evidence requires a separately reviewed policy change, not silent truncation.

## Executed local verification

Linux, Python 3.13.5. Exact-byte source subset, not a full Git checkout: GitHub DNS
from the container is unavailable. The runtime baseline kit was obtained from CI
artifact 11115764744 and checked against its recorded digest; no user-host access.

Command: `python -B -m unittest discover -s tests/research -p 'test_matrix*.py'`.
**27 tests PASS**: 25 new integrity tests and two existing analyzer tests. The
historical-shaped fixture's raw observations are unchanged, but its missing
parent/lifecycle evidence is now correctly BLOCKED. Tests include normal and
resumed positive controls, abnormal exit/timeout/cleanup, identity/hash mismatches,
missing/error/limited traces, duplicate windows, legacy archives, failed script
correlation, semantic non-claims, CLI status and ZIP/JSON resource limits.

Python AST checks and patch whitespace checks apply to all edited sources. The
first local no-index diff wrapper incorrectly required exit 0 even for changed
files; it returned 1 without whitespace diagnostics. This wrapper interpretation
was corrected; no source assertion or application gate was weakened.
A sanity run counted 10,000 synthetic hits in one window in 4.57 ms locally.
That single synthetic timing is not an AE benchmark or a speedup claim.

## Offline replay of previously captured real LLDB evidence

Existing source commit: df13e1b. Artifacts were already downloaded in this chat:

- PR artifact **11116682175**, SHA-256
  `f485723c9ba3a0f169fc7a85e5d7475f3546d051fc2dee65c4583ffb971fb2bd`.
- Push artifact **11115884742**, SHA-256
  `6fbfc9df46ef7b70745fc5042e96eb6a2147f40b1e8af3f26dfe50b5c3912b93`.

Reproduction: verify each ZIP digest/CRC and summary SHA256 sidecar; verify every
stored evidence-file hash. For each of the five parent-bearing summaries per
archive, feed the stored raw result bytes, decoded trace rows and parentAcceptance
object into the new `observer_integrity`. All **10/10** records pass. Repeat with
only debuggerExitCode changed to -11: all **10/10** are blocked. Original bytes
are not edited or uploaded back. The other ten controller-only summaries are not
counted as parent-bearing acceptance records.

This replays old owned-fixture captures. It is not ten new debugger executions,
not proof on AE, and not a fix for the original intermittent timeout in #3.

## Limits and next step

The current matrix archive does not contain its original plan; its planSha256
cannot be independently recomputed by this analyzer. The supplied trace is not
cryptographically authenticated or bound to a live process by this offline check.
No full launch-chain, project identity, callback lifetime, post-commit state,
notification delivery, performance or compatibility gate is closed here.

Full exact-commit CI and its artifacts are recorded separately in PR #2, after
publication to the working branch. Do not substitute the baseline's CI results.
No diagnostic package is handed to the user. Return to the concrete queue callback
thread/context, CommandType-table and WorkQueue emitter/lifetime research gaps;
the retained 19-body report does not need repeating. Historical failures and
records remain intact; main and user projects remain untouched.
