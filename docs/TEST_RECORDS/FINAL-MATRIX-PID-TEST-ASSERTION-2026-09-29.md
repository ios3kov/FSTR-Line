# Final Matrix PID test assertion correction — 2026-09-29

The f3df0c9 runtime logic correctly switched to exact `ps -axo pid=,comm=` matching and the functional assertion already returned only the main AE PID. The remaining CI failure was a malformed test assertion checking whether the list of argv elements literally contained `comm=`; the actual argv element is `pid=,comm=`.

Only the test assertion is corrected to require the exact argv list. No runtime/product behavior changed. Full exact-head push+PR Linux/macOS rerun remains required.
