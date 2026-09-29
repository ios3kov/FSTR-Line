# FSTR Line — текущий статус разработки

Дата: 2026-09-29. Рабочая ветка: integration/host-safety-notifications, Draft PR #2. Main не слит и не изменён.

## Реальные AE evidence

Два реальных runtime trace уже получены на AE 25.6.0.101. Они подтвердили живые BEE/AfterFX internal paths, но command-level Undo/selection markers шумные и второй trace не смог надёжно разделить поздние действия по таймеру.

## Текущий gate: Runtime v4 — интерактивно через Enter

По пользовательскому запросу таймеры для действий удалены полностью.

Сценарий:
1. Terminal показывает ровно одно действие.
2. Пользователь выполняет его в After Effects.
3. Возвращается в Terminal и нажимает Enter.
4. Observer пишет DONE marker и только тогда показывает следующий шаг.

Каждая action window имеет отдельные `<label>-start` / `<label>-done` markers. Это устраняет неоднозначность человеческой задержки предыдущих timed traces.

Набор exact-address кандидатов сохраняет v3: transaction/content boundaries, Undo/selection/switch paths, AfterFX move/trim/switch action markers и playhead candidates. Callback пишет label/role и bounded top-8 stack metadata без target variables/expressions.

Интерактивное ожидание идёт через `/dev/tty`; каждый Enter ограничен 60 секундами, а error/timeout обязан привести к clean detach. Голосовые команды больше не используются.

Перед handoff обязательны push+PR Linux/macOS PASS, unit-тест Enter protocol, exact package, runtime attach smoke, clean source и artifact hash.

SYNC-001 всё ещё NOT RUN. Private production hook не интегрирован.
