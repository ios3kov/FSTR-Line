# Queue collector fixture path correction — 2026-09-30

Run ID: `QUEUE-FIXTURE-20260930-01`.
Baseline: `7d3681b8bb1625e87fb8cb045c06968a85d42786`.
Phase 0 of 5 remains open. Rules and scope are unchanged from
[the collector record](QUEUE-CONTEXT-COLLECTOR-2026-09-30.md).

## Observed failure

The baseline push Integration gate passed all steps:
https://github.com/ios3kov/FSTR-Line/actions/runs/36736334798 .
The baseline mac-research failed the research unit step:
https://github.com/ios3kov/FSTR-Line/actions/runs/36736334774 .
Its log records 135 tests, 11 subtest errors and one Linux-only skip.
Later macOS packaging/smoke steps were skipped, NOT PASS.

All 11 errors were `StopIteration` in the new synthetic fixture's runner,
which matched a canonical tool argument against an unresolved temporary path.
The collector resolves paths; macOS's `/var` temporary path resolves through
`/private/var`. The test fixture did not mirror that normalization. The actual
Apple-tool owned-dylib control was not among the errors, but the overall macOS
gate still failed. This was a test-environment defect, not an AE runtime result.

## Reproduction, change and checks

Added `test_fixture_accepts_a_symlinked_temporary_root`: a test-owned directory
and symlink reproduce the same mismatch on Linux. Before the fix, the new test
failed with exactly the same `StopIteration` stack as macOS CI. The fixture now
canonicalizes its application root once, before constructing its module paths.
No collector guard, test assertion, production code or CI requirement is removed.

Local repeat: 23 tests, 22 PASS and one Apple-tools control NOT RUN/skipped on
Linux; includes the actual LLVM owned Mach-O object control. Python syntax and
whitespace checks PASS. These results apply to the changed test source, not to
real AE. Full exact-commit push/PR checks must verify the containing commit;
the baseline's Linux PASS cannot substitute for the new commit's results.

Collector source remains unchanged from baseline blob
`4b78a935fa6653563f5bed49aa5ae99ca13efb37` (research only; not in CEP package).
No installable user artifact, deployment, release, merge or AE project change.
SYNC-001 queue ordering/thread, clone association, safe registration/context and
actual notification delivery remain UNPROVEN/NOT RUN. Continue the bounded
research plan in the collector record after the tool gate passes.
