# FSTR Line — текущий статус разработки

Дата: 2026-09-29. Ветка: integration/host-safety-notifications, Draft PR #2. Main не изменён.

## Состояние

V5 подтвердил интерактивный parent-terminal protocol и сильный common-path lead `DoProcessProjectChanges`. V6 был подготовлен для structural native coverage, но пользователь попросил объединить все оставшиеся пользовательские проверки в один прогон.

## Final Matrix — один Runtime-AE.command

Один запуск включает две observer sessions:

**До restart:** idle, timing, add/delete/reorder, selection, switch, Undo/Redo, active comp switch, playhead, ExtendScript structural mutation, 20-op ExtendScript burst, 10-click native rapid switch, optional third-party plugin-origin, idle.

После clean detach пользователь вручную сохраняет и закрывает AE, затем вручную открывает тот же AE/project. Parent проверяет исчезновение старого PID и появление одного нового exact process.

**После restart:** idle, timing, Undo/Redo, playhead, ExtendScript mutation, idle.

Перед/после каждого action window собирается read-only state snapshot через официально поддерживаемый macOS DoScriptFile bridge. Snapshots являются after-action oracle, но не доказательством exact post-commit semantics breakpoint entry.

Performance evidence: одинаковый 20-operation ExtendScript burst измеряется до attach и под observer. Native rapid-switch phase даёт ground-truth multiplicity. Raw ratios/counts сохраняются без автоматического claims о duplicates.

Independent other-plugin origin остаётся условным: если установлен сторонний plugin, который реально меняет AE state, его mutation выполняется в выделенном окне. Если такого plugin нет, этот origin будет BLOCKED в том же отчёте; никакой сторонний software не устанавливается/меняется скрытно.

SYNC-001 остаётся NOT RUN до анализа Final Matrix. Private production hook не интегрирован.
