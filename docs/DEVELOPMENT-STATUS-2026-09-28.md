# FSTR Line — текущий статус разработки

Дата: 2026-09-29. Рабочая ветка: integration/host-safety-notifications, Draft PR #2. Main не слит и не изменён.

## Runtime evidence

V5 interactive parent-terminal protocol на AE 25.6.0.101 отработал корректно: PASS, clean detach, 177 hits, все 8 шагов имеют точные start/done markers.

Главный новый lead: `DoProcessProjectChanges` (`BEE.dylib:0x7afa7c`) находится в stack строго внутри timing, selection, switch, Undo, Redo и playhead и отсутствует в обоих idle windows. `Render_EndUndoGroup` покрывает часть timing/switch/playhead, а `BEE_CmdSeekItemToTime` оказался чистым playhead marker.

Это сильная гипотеза общего internal change path, но ещё не notification-source proof и не post-commit proof.

## Текущий gate — Runtime v6

Сохраняется проверенный интерактивный UX:
**одно действие → вернуться в Terminal → Enter → следующий шаг**.

Breakpoints сужены прямо на DoProcessProjectChanges, Render_EndUndoGroup и CmdSeekItemToTime. SetContentChanged/EndGroup оставлены как transaction comparators; selection/switch/Undo/Redo markers — только как ground-truth корреляция.

Матрица v6: idle → move/trim → add layer → delete layer → reorder layer → selection → switch → Undo → Redo → active comp switch → playhead → idle.

Цель v6: проверить structural layer/context coverage общего пути перед тестами ExtendScript и other-plugin origins.

SYNC-001 всё ещё NOT RUN. Private production hook не интегрирован.
