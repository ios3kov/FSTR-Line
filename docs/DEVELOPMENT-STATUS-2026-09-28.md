# FSTR Line — текущий статус разработки

Дата: 2026-09-29. Ветка: integration/host-safety-notifications, Draft PR #2. Main не изменён.

## Final Matrix / common path

Final Matrix остаётся сильным evidence для общего native+ExtendScript change path, restart/reopen и idle controls. SYNC-001 ещё не принят из-за active-comp, post-commit и other-plugin provenance.

## Deep Static — реальный AE результат получен

`FSTR-AE-Deep-20260929T075012Z-33e1ea673c0b.zip`, SHA-256 `1d5b9e6b6a8cadbe360c93d980caa5a4123bafd06a86d35e8e6fc3999b84998d`, PASS на exact AE 25.6.0.101 BEE/AfterFXLib.

Критическая коррекция:
- `DoProcessProjectChanges` entry = **0x7af9f4**;
- исторический runtime boundary **0x7afa7c** = offset +136, сразу после возврата из `BEE_ThreadedRenderUpdateQueue::ProcessFromRenderThread(...)`, а не entry;
- единственный static return = **0x7b055c**.

Historical hits на 0x7afa7c не инвалидируются, но теперь называются `after-process-from-render-thread`.

Concrete active-comp leads:
`CPanoProjComp::Activate/Deactivate/ReActivate`,
`CPanoProjItem::Activate/Deactivate/ReActivate`,
`CItem::ActivateVOut/DeactivateVOut`,
`ScActivateItemPanel` ctor.

## State oracle

Owned-file oracle implementation исправлен и CI-verified. Historical Matrix snapshots не переоцениваются; real validation будет в следующем узком probe.

## Текущий gate — narrow Context/PostCommit positive control

Никакого broad matrix. Один короткий прогон:
idle → comp A→B → comp B→A → timing edit → automatic script marker → idle.

Active-comp PASS требует одновременно:
1. snapshot comp-name реально изменился;
2. exact activate/deactivate candidate сработал в том же окне;
3. idle не показывает ложную активность этого канала.

Post-processing evidence отдельно сравнивает script wall-clock marker after-endUndoGroup с:
- entry 0x7af9f4,
- after-render-thread boundary 0x7afa7c,
- return 0x7b055c.

Даже успешный script timing не будет автоматически обобщён на native post-commit.

Other-plugin provenance остаётся отдельным незакрытым gate.

SYNC-001 остаётся NOT RUN / не принят.
