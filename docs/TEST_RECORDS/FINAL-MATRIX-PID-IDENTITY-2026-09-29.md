# Final Matrix PID identity correction — 2026-09-29

The first Final Matrix CI run failed one new unit test because the test monkey-patched subprocess.run after find_pids had captured it as a default parameter. The test is corrected to inject its runner explicitly.

The same review found a real robustness issue worth fixing before handoff: parsing `ps ... command=` with a prefix match could theoretically classify an executable whose command begins with the AE binary path as the selected main process. Final Matrix now uses `ps -axo pid=,comm=` and requires exact equality with the resolved selected AE executable path. The regression explicitly supplies one main AE path plus an `After Effects Helper` lookalike and requires only the main PID.

No notification candidate, coverage claim or AE action matrix changed. Full push+PR Linux/macOS rerun is required.
