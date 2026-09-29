# Final Matrix safe resume after partial failure — 2026-09-29

The user's failed 8b53832 Final Matrix completed steps 1–12 and aborted during the observed ExtendScript burst at step 13. Because the previous outer process intentionally retained its owned `fstr-final-*` temporary directory on failure, the completed trace/evidence can be reused safely if and only if the same AE process is still running.

Resume acceptance is strict:
- candidate directory age <= 24h;
- no post-restart session exists;
- prior pre-restart plan/result/evidence files are complete enough to inspect;
- current exact AE executable path equals the prior plan executable;
- current AE PID equals the prior attached PID;
- exact breakpoint list equals the current Final Matrix breakpoint list;
- prior observer result is `stage=aborted` with `detached=true`;
- completed actions form a contiguous prefix established by `snapshot-after` evidence.

When all gates pass, the new run imports the old evidence and pre-restart trace as `pre-restart-partial`, tells the user exactly how many steps were completed, and attaches a fresh `pre-restart-resume` observer for only the remaining actions. It then proceeds to the same manual restart/reopen and post-restart matrix. Old evidence is copied, not modified.

If AE has already been restarted, PID mismatches, the project/tool identity is ambiguous, or any resume gate fails, no stale evidence is reused and the tool starts a full clean Final Matrix instead.

This change is specifically to avoid making the user repeat already completed steps while preserving controlled-test identity. SYNC-001 remains NOT RUN until the final report is analyzed.
