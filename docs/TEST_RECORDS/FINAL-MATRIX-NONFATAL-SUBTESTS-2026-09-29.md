# Final Matrix non-fatal subtest policy — 2026-09-29

User runtime evidence reached pre-restart step 13/16 and then the automatic 20-operation ExtendScript burst exceeded the 60-second AppleScript bridge timeout. The outer matrix incorrectly treated `subprocess.TimeoutExpired` as fatal, so later native stress, optional plugin-origin, restart/reopen and post-restart checks were skipped.

Root cause: a subtest-level automation timeout escaped `run_jsx` instead of being returned as evidence.

Correction:
- `run_jsx` now converts AppleScript timeout or launcher failure into a bounded result object with `ok=false` and explicit `timedOut/error`; it no longer throws for these subtest failures.
- A timed-out observed JSX step is marked `step-blocked` and the parent continues the same observer session after the user confirms AE is responsive.
- On timeout the tool explicitly tells the user NOT to re-run the same JSX manually, because the AppleEvent receiver may have continued after the sender timed out.
- A non-timeout auto-launch failure still offers manual Run Script File fallback, but skipping it does not abort the matrix.
- Performance comparison is PASS only if both baseline and observed burst complete successfully; otherwise it is BLOCKED without aborting the functional matrix.
- Snapshot automation failures were already nonfatal through the same return path and remain raw evidence only.

Fatal conditions remain limited to matrix integrity/safety failures: wrong AE/module identity, debugger attach/control corruption, target process crash/exit during an observer session, failure to clean-detach, or invalid restart process identity.

Acceptance: regression proving TimeoutExpired returns a nonfatal result, all previous research/integration tests, exact package, parent↔LLDB macOS smoke, clean source, push+PR Linux/macOS PASS. SYNC-001 remains NOT RUN until the completed matrix is analyzed.
