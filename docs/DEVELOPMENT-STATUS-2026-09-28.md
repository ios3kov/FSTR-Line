# FSTR Line — текущий статус разработки

Дата: 2026-09-28. Ветка: integration/host-safety-notifications.
База main: 15d995e5d27140690c1966f14b2aa0029989a072. Main и исходный Draft PR #1 не изменены и не слиты.
Целевая native-среда: AE 25.6.0.101 / CEP 12 / macOS Apple Silicon.

## Итог

Собрана интеграционная основа с typed Core, усиленными host-операциями, проверяемым CEP-пакетом и визуальными read-only tracks. Это НЕ готовый редактор и НЕ полная интеграция второй ветки. Редактирование из UI не включено до проверки на реальном AE.

SYNC-001 остаётся обязательным: полный прямой источник изменений AE, включая native UI, ExtendScript и другие plugins, timing, слои, порядок, selection/switches, composition/project, playhead и Undo/Redo. Несколько каналов допустимы только при полном совместном покрытии. Polling/revision/idle/focus/self-events не заменяют требование. Текущий источник не найден и не доказан; это не доказательство невозможности.

## Реализовано в интеграционной ветке

- Move использует абсолютные цели, снятые до изменения startTime, вместо повторного сдвига in/out в модели связанных setter-ов.
- Откат касается только затронутых свойств/слоёв, продолжает восстановление после отдельных ошибок, проверяет результат. Неполный откат и неопределённое закрытие Undo блокируют последующие записи.
- Нулевые операции не создают Undo Group. Проверяются типы значений и полная доступность целей до изменения.
- Guard учитывает точное наблюдаемое состояние и ссылки на контекст project/comp; корректность lifetime этих ссылок в реальном AE ещё требует проверки.
- Host больше не зависит от глобального JSON: донорский json2 включён в изолированную область вместе с лицензией.
- Bridge блокирует новые записи после неизвестного результата команды, не повторяет её автоматически и проверяет operationId ответа.
- Визуальные клипы адаптированы к typed snapshot. При ошибках, включая повторные, последние данные остаются видны с явной пометкой STALE.
- Чистый allowlisted пакет dist/cep проверяется по составу, SHA-256, commit/Build ID и dirty-state.
- CI проверяет исходный Core/adapter, настоящий JSX в модели ошибок, скомпилированные UI/bridge, итоговый host-пакет, research tooling и C++ formatter журнала.

## Проверки и границы доказательств

Последний завершённый кодовый этап b428e38c4a75c700eb94a5aebb050dd2bf3fb8e9 прошёл Integration gate: https://github.com/ios3kov/FSTR-Line/actions/runs/36476758819 . Предыдущие отдельные этапы 5d9b457, 225671d и c8114c7 также прошли свой CI. Итоговый commit этого документа имеет собственный новый Build ID и должен проверяться своим workflow run; успех предыдущего SHA не переносится автоматически.

У донорских v4 CI actions наблюдалось предупреждение о Node 20 runtime. Они заменены на проверенные SHA v6 с Node 24 runtime, без ослабления permissions/проверок; новый workflow также требует собственного PASS. Код продукта продолжает тестироваться на Node 22. Локальные Python-проверки исследовательских средств: 14/14, только synthetic binaries/fake debugger frames.

Все эти результаты — Level 1, не runtime PASS в After Effects. SDK-плагин, реальный debugger attach, ABI и истинный Undo/Redo здесь не проверены. Детали: TEST_RECORDS/HOST-SAFETY-2026-09-28.md, UI-INTEGRATION-2026-09-28.md, INTERNAL-RESEARCH-TOOLS-2026-09-28.md.

## Внутренние уведомления: отдельное исследование

В DEVELOPMENT_RULES.md нет категорического запрета на private-hook research. Пользователь разрешил изолированное исследование, но не применение непроверенного механизма в production. Текущий план и инструменты: ../research/ae-notifications/README.md; полная матрица: ../research/ae-notifications/coverage.json.

Готовы read-only извлечение идентичности Mach-O/UUID/SHA-256, bounded symbol/string leads и opt-in LLDB callback logger с проверками PID/module UUID и ограничением захвата. Они не запускают AE, не присоединяются к процессу, не ставят breakpoint автоматически и не подменяют отсутствие реального кандидата вымышленным API.

Важное исправление прежнего вывода: priority=0 в loaded-записи command probe был передан самим probe, а не получен из command callback AE. Исторические логи сохранены; пояснение и тест: TEST_RECORDS/COMMAND-PROBE-ERRATA-2026-09-28.md.

Реальный этап binary inspection/debugger tracing сейчас BLOCKED: точные бинарники AE и авторизованный процесс Mac недоступны в этой сессии. Поиск строк на искусственных данных не является исследованием внутренностей Adobe. Нет найденного internal hook, нет post-commit evidence и полной runtime coverage.

## Оставшийся объём

1. На изолированном AE проверить точную сборку, timing/keyframes/stretch/remapping, идентичность project/comp, Undo/Redo и восстановление после исключений.
2. Снять identity реальных модулей, исследовать symbols/strings/cross-references, установить положительный контроль, проследить конкретные функции и доказать notification/post-commit semantics по всей матрице. Только после кандидата — отдельный native diagnostic probe.
3. Закончить перенос совместимых donor-наработок: installer/runtime runner/performance harness требуют адаптации к canonical contract. См. DONOR_INTEGRATION.md.
4. После native editing gate включить editing UI; затем drag/trim, multi-selection, snapping, ruler/playhead, zoom/scroll, virtualization и real-device/performance приёмка.

Subframe timing пока явно отклоняется, не округляется молча; это незакрытое ограничение, а не законченная поддержка. Windows/Intel и distributable signing также не приняты. Ни merge, ни release, ни изменения установленного AE этим этапом не выполнены.
