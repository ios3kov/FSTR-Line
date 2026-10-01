# Runtime v5 — parent-owned interactive Terminal protocol — 2026-09-29

User ran v4 and observed only the initial action list followed by FAIL; no step-by-step prompt appeared. The v4 architecture placed /dev/tty interaction inside LLDB's embedded Python execution. Regardless of the exact inner failure, that architecture did not satisfy the observed UX contract.

V5 moves all human interaction out of LLDB. The launcher process that already prints normally in Terminal now owns input/output. LLDB is started as a separate child with stdin=/dev/null and a private log. Parent and LLDB exchange only bounded JSONL commands/acknowledgements in the owned temporary directory.

Exact protocol:
- LLDB attaches, verifies exact loaded module UUIDs and exact breakpoint locations, starts capture and continues AE.
- LLDB writes READY acknowledgement.
- Parent prints one Russian action.
- Parent sends <label>-start and waits for LLDB acknowledgement before showing the instruction.
- User performs the action, returns to the same Terminal and presses Enter.
- Parent sends <label>-done and waits for acknowledgement before showing the next action.
- After the final Enter parent sends FINISH; LLDB pauses only for clean capture stop/detach.
- Ctrl-C/EOF/error sends ABORT best-effort and routes to clean detach.

No fixed human timing gaps exist. IPC acknowledgements are bounded (10 s), initial ready is bounded (30 s), and the existing total capture bound remains 540 s. The parent terminal input is never consumed by LLDB.

Predeclared gates: pure unit order/Enter/IPC/child-exit tests; all existing research and integration gates; exact packaged runtime; macOS owned-fixture attach using the same parent/LLDB JSONL protocol, actual breakpoint hits, start/done phase markers and clean detach; push+PR Linux/macOS PASS; exact artifact hash before handoff.

Breakpoint candidates are unchanged from v4. SYNC-001 remains NOT RUN.
