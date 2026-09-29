# Deep static report completeness — 2026-09-29

Baseline b23c1db. During preparation for completion-event correlation, review
found that deep_static.main ignored nested tool exit codes and truncation when
assigning overall PASS. This is a diagnostic correctness defect, not evidence
of a production notification failure.

Acceptance: a failed symbol/disassembly tool, limited symbol output, missing
exit code or empty analysis cannot produce an overall PASS. Preserve nested
diagnostics in the archive, return 2 for BLOCKED, keep SYNC-001 NOT RUN.

Added analysis_complete and integrated it before archive generation. Tests
cover normal completion, tool errors, missing code, limited output, empty
analysis and main's actual archive/exit result. The integration test uses
mocked tool results and a unique temporary directory; no Adobe process runs.

Baseline reproduction: executed the new archive test against deep_static.py
loaded directly from `git show HEAD:research/ae-notifications/deep_static.py`
before committing the fix. It failed with `0 != 2` and printed PASS despite
the injected disassembly exit code 1. Fixed version returns BLOCKED/2.

Verification: `python3 -B -m unittest discover -s tests/research -p 'test_*.py'`
— 100 tests PASS on macOS arm64; `git diff --check` PASS. Product sources and
CEP packaging unchanged. Real AE completion correlation remains NOT RUN.

Limits: this gate checks tool completion, not whether a successful tool found
every expected symbol or proved a semantic assertion. Exceptions still fail
the process rather than creating a successful archive. Existing historical
reports are not rewritten or retrospectively reclassified without their raw
tool results. Next: prepare the controlled completion-event correlation probe;
do not invoke the existing interactive/restart matrix on user-owned AE state.
