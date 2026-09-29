# FSTR Line — текущий статус разработки

Дата: 2026-09-29. Рабочая ветка: integration/host-safety-notifications, Draft PR #2. Main не слит и не изменён.

## Runtime research

Два реальных AE runtime trace подтверждают живые internal BEE/AfterFX paths, но полный notification source ещё не доказан. V3/V4 добавили transaction/content boundaries, exact action markers, labels/roles и bounded stack evidence.

## Текущий gate: Runtime v5

V4 не дал пользователю интерактивных шагов: Terminal напечатал список и runtime завершился FAIL до первого action prompt. Архитектура исправлена, а не замаскирована.

Теперь Terminal UX полностью принадлежит внешнему launcher:
**одно действие → пользователь делает его в AE → возвращается в Terminal → Enter → следующий шаг.**

LLDB больше не читает /dev/tty и получает stdin=/dev/null. Parent launcher и LLDB controller синхронизируются приватными JSONL command/ack файлами в owned temp directory. Каждый start/done marker подтверждается LLDB до перехода дальше.

Breakpoint set остаётся exact-address v4: BEE transaction/content boundaries, Undo/selection/switch candidates, AfterFX move/trim/switch action markers и playhead candidates. Callback не вызывает target private API и не читает target variables/project contents.

Перед handoff обязательны unit protocol tests, exact package, real macOS parent/LLDB IPC attach smoke with breakpoint hits + start/done markers + clean detach, push+PR Linux/macOS PASS and exact artifact hash.

SYNC-001 всё ещё NOT RUN. Private production hook не интегрирован.
