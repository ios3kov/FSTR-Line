# Actual macOS tooling acceptance and bounded handoff — 2026-09-28

## Historical runs (not rewritten)

c9da73bcce1a74654a09dfbc5a04d5988dfff22e: Linux integration PASS; macOS unit tests 30 PASS, exact collector ZIP read the compiler-built Mach-O, but LLDB control FAIL (run 36483043035). No failed kit was handed to the user. The harness initially did not persist the inner LLDB exception.

a624109631fa7574f018d24547adbea2b8fb71b3: the recorder was explicitly imported into LLDB command scope and failure details were persisted. macOS 15.7.9 arm64, Xcode 16.4, Apple clang 17.0.0, LLDB 1700.0.9.502, Python 3.14.7. Run 36483245029 / job 109133791407 PASS: 30 Python tests; actual packaged collector on a compiler-built Mach-O; UUID independently matched dwarfdump; real LLDB observed 3 of 3 expected calls from our own C++ fixture; normal process exit; source tree clean. SHA-256 of that historical diagnostic kit: 867130aaca64301f51fdb99595c0a3eb57fc82173f6b53210ee81fd71fa8f9e8. This is NOT an AE runtime run and not the hash of subsequent candidates.

## Final review changes and checks

A final source review identified incomplete accounting after a failed inspector, a possible FAIL-to-BLOCKED downgrade after a later timeout, and os.walk's default silent skipping of inaccessible directories. The collector now reserves input bytes before each attempt, preserves the most severe failure and explicitly reports unreadable directories. Three targeted regressions were added; all 19 new collector tests pass locally on Linux. Both existing integration and macOS package/LLDB gates must rerun on the resulting commit; no previous SHA's PASS transfers automatically.

The handoff ZIP now uses fixed canonical ZIP metadata (1980-01-01, explicit UNIX modes) and stored entries, avoiding timestamp and compression-library drift. Build identity remains the actual source commit in build-manifest.json. Canonical timestamp is archive normalization, NOT the development date. The delivered bytes must match the SHA printed in the final successful macOS run; do not substitute an unverified rebuild. This diagnostic archive is separate from the CEP artifact.

## Unchanged product status

SYNC-001 is mandatory and NOT RUN here. No actual Adobe binaries, notification candidates, internal cross-references or post-commit events have been inspected in this session. A passing actual-LLDB positive control on our fixture establishes the measuring tool, not notification coverage in AE. Next required evidence is one read-only bundle-collection report from the user's exact AE 25.6 installation; no Adobe binaries are requested for public storage. After real leads, run an AE-specific positive control and the full native/script/plugin coverage matrix. No polling substitution, no merge or product deployment.
