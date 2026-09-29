# FSTR Line — текущий статус разработки

Дата: 2026-09-29. Ветка: integration/host-safety-notifications, Draft PR #2. Main не изменён.

## SYNC-001 research coverage

**Origins/coverage research: OBSERVED. Production integration: BLOCKED.**

Real AE 25.6.0.101 evidence now covers:
- native UI timing/add/delete/reorder/selection/layer switches/Undo/Redo/playhead;
- ExtendScript-origin changes before/after restart;
- active composition changes with independent state oracle;
- independent AEGP plugin-origin mutation with direct stack provenance;
- restart/reopen;
- script-origin post-endUndoGroup processing positive control.

Latest final plugin-origin report:
`FSTR-AE-PluginOrigin-20260929T090335Z-1a2a1e564b15.zip`, SHA-256 `dad9249991e0383b752c06cf960052fd5ca611c8ad47e9ae175d48abefcc4068`.

Acceptance facts:
- snapshot before L1 video active = 1;
- helper provenance = 1→0, status 0;
- snapshot after L1 video active = 0;
- exact state/helper correlation = PASS;
- BEEp_SetLayerSwitch = 2 hits;
- project-processing boundary = 3;
- DoProcessProjectChanges return = 3;
- clean detach = PASS;
- stack contains FSTRPluginOrigin → AEGPDriver → AfterFXLib → BEE.

The independent other-plugin origin research gate is therefore closed.

## What remains before SYNC-001 can be accepted

LLDB breakpoints are not a shipping mechanism. Production acceptance still requires:
1. a defined compatible/failure-safe internal delivery mechanism (or later supported Adobe API);
2. exact-build/version mismatch refusal and recovery behavior;
3. post-commit state-read semantics for the actual shipping mechanism across required change families;
4. duplicate/coalescing/missed-event behavior, rapid bursts, no-op/error/cancel and panel-closed cases;
5. uninstrumented CPU/memory/playback responsiveness comparison against baseline;
6. compatibility/safety/maintenance/licensing review before any private production integration.

Polling/revision/idle/focus/self-events remain non-compliant substitutes.

SYNC-001 remains NOT RUN as a production integration gate.
