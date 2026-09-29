# FSTR Line — текущий статус разработки

Дата: 2026-09-29. Ветка: integration/host-safety-notifications, Draft PR #2. Main не изменён.

## Final Matrix — проанализирован

Реальный `FSTR-AE-FinalMatrix-20260929T072338Z-2daebc3abe79.zip` (SHA-256 `12f0de676336fe2fc61dd6f8692b77d5d52e32cec67fef3c542009b58ad5d2d4`) полностью завершён на AE 25.6.0.101. Обе LLDB sessions PASS/clean detach; restart подтверждён сменой PID 80268 → 96103.

`DoProcessProjectChanges` напрямую наблюдался для native timing/add/delete/reorder/selection/switch/Undo/Redo/playhead и для ExtendScript до/после restart. В idle windows — 0. Это сильный common-path lead, но не production notification API и не one-event-per-change контракт.

Открытые доказательные долги:
- active composition switch: 0 candidate hits → отдельный direct channel нужен;
- post-commit: UNPROVEN; нормальные окна имеют последний ProcessProjectChanges после известных markers, но burst даёт контрпример;
- state snapshot oracle невалиден: DoScriptFile возвращал 0 вместо строки состояния;
- other-plugin window содержит hits, но provenance стороннего plugin не доказан;
- LLDB burst overhead 14.579x нельзя переносить на production performance.

## Текущий этап

По DEVELOPMENT_RULES следующий gate сначала статический и read-only:
1. exact SHA+UUID validation реальных BEE/AfterFXLib;
2. bounded static disassembly `DoProcessProjectChanges` и известных boundary/playhead functions;
3. symbol discovery для active-comp/composition/viewer activation;
4. reproducible offline Final Matrix analyzer;
5. только после конкретных static leads — узкий runtime positive control, если он действительно нужен.

Никакого нового broad matrix, polling-substitute, merge/deploy или private production hook на этом этапе нет.

SYNC-001 остаётся NOT RUN / не принят.
