# FSTR Line — текущий статус разработки

Дата: 2026-09-28. Рабочая ветка: integration/host-safety-notifications, Draft PR #2. Main не слит и не изменён.

## Продукт

Typed Core, versioned commands/guards, усиленный host, проверяемый CEP package и read-only visual clips существуют. Editing UI остаётся закрытым до реальной AE-проверки.

SYNC-001 остаётся обязательным: полный прямой поток AE-originated изменений для native UI, ExtendScript и других plugins, включая timing, layer add/delete/reorder, selection/switches, project/comp, playhead и Undo/Redo. Polling/revision/idle/focus/self-events не заменяют требование.

## Реальные AE evidence

Статический этап на AE 25.6.0.101 подтвердил точные SHA/UUID BEE.dylib и AfterFXLib и внутренние BEE/Undo/Selection/AfterFX symbols.

Первый настоящий runtime trace получен: `FSTR-AE-Runtime-20260928T221042Z-f348ac55b6db.zip`, SHA-256 `569fd656d255a481c438fc934177f1ef6d83b80fbb6ffc5c58965b70949b2144`. Observer из clean commit `039025fbed28518d8f8dc65d5843221ea816f6d2` успешно attached к AE, записал 392 hits и clean-detached.

Подтверждено в runtime:
- `BEE_Undo` вызывается, но шумный: 22 hits, включая 17 во время live timing edit. Это не уникальное Undo notification.
- `BEE_Redo`: 2 hits вокруг реального Redo; command marker, не общий change source.
- `BEE_SelectLayer`: 6 hits вокруг selection-related UI; кандидат пути selection, не post-change proof.
- `OnUndoCommandCompleted`, `BEE_CmdModifySelection`, project-settings post: 0 hits в текущей матрице.
- широкие `CmdParamChanged/Pre` breakpoints признаны невалидными: они попадали в unrelated function на `0x5c70`.

SYNC-001 всё ещё NOT RUN: runtime hits не доказывают post-commit state, полное coverage или production subscription.

## Текущий gate

Runtime observer v2 переводится на точные module file-address breakpoints. Цели: AVLayer timing change, Undo state transitions, concrete selection mutation, AfterFX layer-selection update и RealtimeNeedle/playhead. Action windows расширены; один action на фазу.

Перед handoff обязательны: unit/integration, exact packages, real macOS LLDB controls, exact-address attach smoke с реальным hit и clean detach, clean source и artifact identity. Затем нужен второй AE runtime trace.

После этого: post-commit oracle, ExtendScript + other-plugin origins, structural layer/context changes, duplicates/misses/restart/performance. Private hook в продукт ещё не интегрирован.
