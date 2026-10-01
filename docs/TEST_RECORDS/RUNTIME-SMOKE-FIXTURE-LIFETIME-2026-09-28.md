# Runtime attach smoke fixture lifetime — 2026-09-28

On exact commit fb7dd4d the push macOS run passed the runtime attach smoke, while the duplicate PR macOS run failed at clean detach because the owned fixture had already exited. The fixture originally lived about four seconds; LLDB startup/attach time varies across hosted runners, so this was nondeterministic.

The production controller is intentionally unchanged: an AE process that exits during a capture is not accepted as a clean PASS. Only the owned test fixture lifetime is extended to about forty seconds, well beyond the two-second capture; the test still terminates only its own fixture in finally.

Both push and PR macOS gates must pass on the new exact commit before handoff.
