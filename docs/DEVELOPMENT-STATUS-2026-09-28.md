# FSTR Line — текущий статус разработки

Дата: 2026-09-29. Ветка: integration/host-safety-notifications, Draft PR #2. Main не изменён.

## Evidence already observed

Real AE 25.6.0.101 evidence confirms native project-change coverage, ExtendScript origin, active-comp transitions, real state oracle, restart/reopen and script-origin post-processing after endUndoGroup.

## Other-plugin helper — helper mutation observed, direct correlation still pending

Real report `FSTR-AE-PluginOrigin-20260929T084238Z-fcf93b543315.zip`, SHA-256 `111c386934f41448c56b3e79908fb9b4d0f593b37d4d2b9c65d8334829f6493c`.

The installed diagnostic AEGP helper is real and functional:
- exact Build ID/source receipt present;
- public-SDK mutation log shows first-layer VIDEO_ACTIVE `1 → 0`;
- independent state oracle also shows L1 `1 → 0`.

The direct-channel observer did not overlap the mutation: the action window lasted ~50.6 ms and detached roughly 2.47 s before the relevant helper mutation. Hence directHitCounts={} is a timing/protocol failure, not negative candidate evidence.

## Current fix

Observe workflow is now mutation-driven instead of Enter-driven:
1. observer records current helper-log sequence baseline;
2. writes `plugin-origin-start`;
3. user clicks Window → FSTR Plugin Origin Test once;
4. Terminal automatically waits for a new exact-Build-ID `mutationEnd`;
5. keeps LLDB active another 1.5 s for downstream processing;
6. writes done and detaches.

No helper rebuild/reinstall is required. Updated observer explicitly accepts the currently installed helper source commit `d5a86afe...`.

SYNC-001 remains NOT RUN / not accepted until this corrected overlap run proves other-plugin direct-channel correlation and production performance/stability gates are addressed.
