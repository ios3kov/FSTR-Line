# Runtime attach smoke correction — 2026-09-28

Historical commit e2d996b7 reached the attach stage on GitHub macOS successfully and detached the owned fixture cleanly. The smoke then failed because its test-only C symbol regex expected `fstr_runtime_candidate()`, while LLDB exposes the extern "C" symbol as `fstr_runtime_candidate` without a C++ argument-list suffix. The production AE candidate regexes are based on observed demangled C++ LLDB summaries and are unchanged.

The smoke fixture regex is corrected only for the C fixture. No production candidate, location bound, module identity check, attach policy or callback semantics are relaxed. The focused nm reader also explicitly closes its stdout pipe after child completion/termination, addressing Python 3.14 ResourceWarning observed in the same CI run.

Required rerun: all unit/integration gates, exact packages, existing LLDB control, focused smoke, runtime attach smoke with >=1 owned-fixture hit and clean detach, clean source and artifact identity. Actual AE runtime remains NOT RUN.
