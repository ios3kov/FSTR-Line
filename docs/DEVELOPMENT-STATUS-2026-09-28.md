# FSTR Line — текущий статус разработки

Дата: 2026-09-28. Рабочая ветка: integration/host-safety-notifications, Draft PR #2. Main не слит и не изменён.

## Продукт

Typed Core, versioned commands/guards, усиленный host, проверяемый CEP package и read-only visual clips существуют. Editing UI остаётся закрытым до реальной AE-проверки.

SYNC-001 остаётся обязательным: полный прямой поток AE-originated изменений для native UI, ExtendScript и других plugins, включая timing, layer add/delete/reorder, selection/switches, project/comp, playhead и Undo/Redo. Polling/revision/idle/focus/self-events не заменяют требование.

## Реальное статическое Evidence с AE 25.6.0.101

Пользовательский отчёт `FSTR-AE-Static-20260928T213703Z-cd1461c05b83.zip` идентифицировал AE 25.6.0.101 и успешно прочитал 256 реальных Mach-O модулей. Общий collection status BLOCKED только из-за заранее заданного module/time/byte budget; это не полный scan приложения.

Главные leads:
- `BEE.dylib` SHA-256 `817b9de9c6d57b5d6988b634842090e1528fe817a5685c8d1ff358553c6660ca`, UUID `161300f3-73f8-3ebc-a751-959df40a073b`.
- `AfterFXLib` SHA-256 `ce3aa2f16fe5449a77379a6b622e1a221596e511b86f7708dd3e2f7a3cced01a`, UUID `edc800d6-9e4b-3a03-9bbb-8239f3f6eea5`.

Пользовательский focused-report `FSTR-AE-Focused-20260928T215138Z-3561b71586d7.zip`, SHA-256 `0609b3de91f67f56e942708438f575f1d89fb46440e9bf0b95f98f3bf4165e93`, подтвердил LLDB identity BEE и AfterFXLib и дал адресуемые internal функции:
- `BEE_UndoContext::OnUndoCommandCompleted()` — BEE file address `0x649c6c`.
- `BEE_UndoContext::GetUndoCommandCompletedSignal()` — `0x64a6fc`.
- `BEE_Undo(BEE_UndoContext&)` — `0x645958`.
- `BEE_Redo(BEE_UndoContext&)` — `0x645f24`.
- `BEE_CmdModifySelection(...)` — `0x5580c`.
- `BEE_SelectLayer(...)` — `0x302a8`.
- несколько derived `::CmdParamChanged(...)` / `::CmdPreParamChange(...)`.
- AfterFXLib ссылается на `BEE_UndoContext::GetUndoCommandCompletedSignal` и содержит `PostMessageToUIThread<...MessageNameForProjectSettingsChangedMessage...>`.

Focused report имеет общий status BLOCKED, потому что дополнительный raw-Mach-O-name lookup в BEE завершал LLDB с code 1 после уже успешного regex lookup. Исторический FAIL сохранён; это не отменяет конкретные адреса/UUID из успешной части отчёта. Инструмент исправлен: raw nlist spelling больше не считается callable LLDB name, а большой nm output обрабатывается потоково.

Это **реальные private static leads**, но ещё не production notification source. Статика не доказывает направление callbacks, post-commit состояние, полноту coverage, ABI stability или возможность безопасной подписки.

## Текущий gate: наблюдательный runtime probe

Подготовлен attach-only runtime observer, pinned к exact AE 25.6.0.101 и указанным SHA/UUID. Он:
- не запускает и не завершает AE;
- не вызывает private функции;
- не использует EvaluateExpression;
- не читает target variables / project contents;
- не пишет target memory;
- ставит только regex breakpoints на уже подтверждённые internal functions;
- логирует timestamp/thread/function/module UUID/file address;
- каждый hit сохраняет как `commitPhase=UNKNOWN`, `isNotificationProven=false`.

Начальный native-UI matrix: idle → timing move/trim → selection → switches → Undo → Redo → playhead → idle. Phase markers нужны только для correlation. ExtendScript и other-plugin origins, post-commit oracle, layer add/delete/reorder, context changes, duplicates/misses и performance остаются отдельными обязательными gates.

MacOS CI уже подтвердил, что LLDB может attach/detach owned fixture и разрешает breakpoint location; несколько исторических smoke defects в test harness (fixture regex, setter return semantics, syntax corruption) сохранены в TEST_RECORDS и исправлены без ослабления production candidate rules. Финальный exact-commit gate должен пройти полностью перед передачей runtime artifact пользователю.

## Что остаётся

SYNC-001 = NOT RUN до настоящего AE runtime trace и полной матрицы происхождений/изменений. Никакой private hook пока не интегрирован в продукт. Main, установленный AE и production не менялись.

После runtime observation:
1. отвергнуть/оставить кандидаты по реальным hits;
2. добавить независимый post-commit state oracle;
3. проверить native UI + ExtendScript + other-plugin origins и полный SYNC-001;
4. только затем рассматривать способ production subscription и compatibility strategy;
5. параллельно остаются donor installer/runtime/performance harness, editing UI/gestures, subframe timing, Windows/Intel и signing/release.
