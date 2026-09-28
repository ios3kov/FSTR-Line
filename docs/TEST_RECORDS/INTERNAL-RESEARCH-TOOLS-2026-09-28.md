# Isolated research tooling — 2026-09-28

Prerequisite: DEVELOPMENT_RULES.md review and user authorization of internal-notification research. Baseline product branch: c8114c718afcd26f797990668d4f472de2ecc21d (Integration gate PASS, run 36475840172). The research tools are outside the CEP package.

Implemented: read-only exact-binary identity, Mach-O/fat CPU/UUID and bounded symbol/string lead extraction; explicit partial-scan flags; unique output; input-change detection; no binary execution or modification. Optional LLDB callback logger binds an explicitly supplied PID and module UUID identities, records only candidate hits and pauses on mismatch/error/capture limits. It never attaches, creates a breakpoint, guesses a candidate or evaluates target code. Native command logger no longer mislabels synthetic load priority as observed AE callback data; an additive erratum preserves historical evidence.

Local evidence: Python 3.13.5/Linux, synthetic Mach-O files and fake LLDB frames, 14 tests PASS after fixing bytearray magic handling. Neither fixture symbols nor fake frame functions are AE candidates. The exact Git commit's CI reruns these tests together with TypeScript/host/UI/CEP packaging checks and a logger-only C++ formatter harness. The C++ harness uses scalar stand-ins, not the Adobe SDK; it cannot validate plugin ABI or runtime delivery.

Native AE application binary inspection: BLOCKED (exact binary not available). Actual LLDB tracing: BLOCKED (no authorized AE process/Mac debugger available through this session). Native plugin SDK build/load: NOT RUN. Full notification coverage, post-commit state and native responsiveness: NOT RUN. The remaining scope is in research/ae-notifications/coverage.json and README.md; a missing tool environment does not imply that an internal mechanism cannot exist.

No private production hook is installed, no Adobe binary/SDK is redistributed and no existing project/preferences/security setting is changed. SYNC-001 is unchanged and is not replaced by polling.
