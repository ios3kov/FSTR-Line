# FSTR Line — текущий статус разработки

Дата: 2026-09-29. Рабочая ветка: integration/host-safety-notifications, Draft PR #2. Main не слит и не изменён.

## Продукт

Typed Core, versioned commands/guards, усиленный host, проверяемый CEP package и read-only visual clips существуют. Editing UI остаётся закрытым до реальной AE-проверки.

SYNC-001 обязателен: полный прямой поток AE-originated изменений для native UI, ExtendScript и других plugins, включая timing, layer add/delete/reorder, selection/switches, project/comp, playhead и Undo/Redo. Polling/revision/idle/focus/self-events не заменяют требование.

## Реальные AE runtime traces

Первый trace подтвердил, что BEE Undo/Redo/SelectLayer действительно вызываются в живом AE, но command-level hooks шумные; broad CmdParamChanged regex был ложным и удалён.

Второй trace `FSTR-AE-Runtime-20260929T060524Z-8f6562f3cc77.zip`, SHA-256 `ff6cb21dcbc59c0d2dd0daea8105b0c9eae6c13ed0f56ad6c7a350f9e1748984`, получен exact-address observer v2. Attach/setup/capture/detach PASS; 39 hits. Все hits произошли до scheduled selection phase, поэтому trace не используется как отрицательное доказательство для later actions.

Observed v2: Undo 10, SetExecutingUndo 10, CLayerSelection::SetSelection 6, BEE_Selection::Add 6, SelectLayer 3, Redo 2, SetExecutingRedo 2. Даже idle-control содержит эти command/selection hits, значит они не являются достаточным универсальным source.

## Текущий gate: runtime v3 correlation

Без нового полного scan используются уже подтверждённые exact addresses:
- transaction/content boundaries: FinishCurrentTransactionIfAny, FinishCurrentTransaction, StartTransaction, SetContentChanged, EndGroup, PushUndoTask;
- Undo completion signal operator;
- BEEp_SetLayerSwitch;
- selection/Undo markers;
- AfterFX native UI action markers for move/trim/time command/switch;
- existing playhead candidates.

Каждый breakpoint получает label/role. Callback пишет только bounded stack metadata (до 8 frames: function/module UUID/module name/file address), без target variables/expressions. Runtime protocol голосом объявляет русские фазы через macOS `say`, чтобы пользователь мог оставить AE foreground и не выполнять действия раньше marker.

Перед handoff обязательны все unit/integration gates, exact runtime package, macOS exact-address labeled attach smoke with actual hits+stack+clean detach, clean source and artifact identity.

SYNC-001 всё ещё NOT RUN. Private production hook не интегрирован.
