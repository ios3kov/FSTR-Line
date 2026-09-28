# Runtime smoke fixture syntax correction — 2026-09-28

The previous automated edit of the test-only fixture regex corrupted mac_runtime_attach_smoke.py and duplicated its tail. Unit discovery did not import mac_*.py, so the syntax error surfaced only at the macOS smoke step. This is a test harness defect; production runtime observer files were not changed by the bad replacement.

The smoke file is rewritten cleanly with the intended extern-C regex `^fstr_runtime_candidate$`. A new cross-platform unit test parses every mac_*.py smoke script and the runtime/focused research entrypoints with Python AST so syntax corruption is rejected during Research unit regression before packaging.

The historical attach evidence from e2d996b remains useful only for one fact: LLDB successfully attached to and detached from the owned fixture before failing on the test regex. No AE runtime claim follows.

All gates must rerun on the corrected commit. No failed runtime package is handed off.
