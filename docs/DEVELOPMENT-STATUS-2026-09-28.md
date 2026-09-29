# FSTR Line — текущий статус разработки

Дата: 2026-09-29. Ветка: integration/host-safety-notifications, Draft PR #2. Main не изменён.

## Evidence summary

Real AE 25.6.0.101 evidence now confirms:
- common project-change processing for native timing/add/delete/reorder/selection/switch/Undo/Redo/playhead;
- ExtendScript origin before/after restart;
- active composition transitions via exact `CItem::DeactivateVOut()` + `CItem::ActivateVOut()` correlated with state-oracle comp-name changes;
- owned-file state oracle on real AE;
- restart/reopen;
- script-origin post-processing after `endUndoGroup`.

Latest post-commit report:
`FSTR-AE-Context-20260929T081250Z-b6f1f48ae274.zip`, SHA-256 `8611ed24247122810d604710165b75ca32913473f38225e421c237fd327245b6`.

Marker timing:
- before 1790669562027 ms, enabled=1
- after mutation 1790669562130 ms, enabled=0
- after endUndoGroup 1790669562156 ms, enabled=0
- first after-ProcessFromRenderThread boundary after endUndoGroup: +46.631 ms
- first DoProcessProjectChanges return after endUndoGroup: +75.062 ms

State snapshot after the action independently confirms enabled=0.

This is positive evidence for the tested script origin, not a universal native post-commit contract. Idle project-processing cycles remain, so project-processing points are wake/work boundaries, not one logical event per mutation.

## Current final evidence gap — other-plugin provenance

Research confirmed a public-SDK-only diagnostic path:
`GetActiveItem → GetCompFromItem → GetCompLayerByIndex(0) → GetLayerFlags → StartUndoGroup → SetLayerFlag(VIDEO_ACTIVE) → EndUndoGroup`.

A separate diagnostic AEGP helper is being added. It:
- is not production FSTR;
- registers `Window → FSTR Plugin Origin Test`;
- mutates only the first layer's VIDEO_ACTIVE flag when explicitly invoked;
- writes a PID/build-specific provenance JSONL log under /tmp;
- uses public AEGP suites only;
- has a distinct Build ID/source commit so observer hits can be correlated to an independent plugin-origin mutation.

No automatic install/restart, merge/deploy, security change or production private-hook integration is performed by repository CI.

SYNC-001 remains NOT RUN / not accepted until plugin-origin provenance is proven and remaining production performance/stability gates are addressed.
