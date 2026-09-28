# FSTR Line — текущий статус разработки

Дата: 2026-09-28. Рабочая ветка: integration/host-safety-notifications, Draft PR #2. Main и исходный Draft PR #1 не слиты и не изменены.

## Продукт

Есть typed Core, versioned snapshot/commands/guards, усиленные host-операции, проверяемый CEP-пакет и визуальные read-only клипы. Это НЕ готовый редактор. Editing UI остаётся закрытым до реальной проверки timing, ключей/stretch/remapping, Undo/Redo и восстановления после ошибок в AE.

**SYNC-001 обязателен: полный прямой источник уведомлений от AE**, включая native UI, ExtendScript и другие plugins, timing, создание/удаление/порядок слоёв, selection/switches, composition/project, playhead и Undo/Redo. Допустим проверенный набор каналов с полным совместным покрытием. Polling/revision/idle/focus/self-events не заменяют требование.

В DEVELOPMENT_RULES.md нет категорического запрета на изолированное private-hook research. Найденный внутренний вызов сам по себе не доказывает готовность механизма к production. Источник ещё НЕ найден и НЕ реализован; это не доказательство невозможности.

## Подтверждённые предыдущие этапы

13ea401d51f3636e2cf8eaa1e029b166c0d9f738: 93 tests PASS, build/package/clean identity PASS. Усилены откат и блокировка неопределённых записей, исключён повторный сдвиг in/out в модели связанных setter-ов, добавлен независимый JSON и сохранение STALE-проекции. Историческое ошибочное чтение priority=0 у command probe исправлено отдельным erratum, старые логи сохранены. Это Level 1 без настоящего AE.

7b21e50b64df2f7599e65c9d91795629e7c890a0: Linux/macOS CI PASS; точный collector ZIP на нашем Mach-O, сравнение UUID с dwarfdump, 3/3 вызова нашей контрольной программы через настоящий LLDB. f9090f57de4ded26aa09f7a4602f3444ae2b6778: Linux/macOS CI PASS для явного выбора .app и подробной диагностики отказов. Результаты и hashes сохранены в PR #2. Эти тесты подтвердили инструменты в своём scope, не корректность предположения об идентификаторе настоящего AE.

## Текущий этап: исправлен ошибочный ожидаемый Bundle ID

Новый пользовательский отчёт FSTR-AE-Static-20260928T212314Z-35fa34495692.zip показал точную причину: выбранный Adobe After Effects 2025.app сообщает com.adobe.AfterEffects.application, 25.6.0, build 25.6.0.101, executable After Effects. Сборщик ошибочно ожидал com.adobe.AfterEffects. Приложение было выбрано, но отвергнуто до чтения модулей. Это дефект сборщика, не ошибка выбора пользователя.

Исправлена точная проверка Bundle ID; версия, путь, symlink и read-only ограничения сохранены. Добавлен независимый metadata fixture из отчёта и 7 regression-тестов. Старый collector воспроизводит FAIL, исправленный проходит 7/7 локальных проверок. Ранние тесты повторяли неверный идентификатор из кода; их fixtures также исправлены.

macOS smoke теперь проверяет точный ZIP с наблюдаемыми метаданными и именем After Effects на НАШЕМ скомпилированном Mach-O, включая UUID/SHA и настоящий LLDB положительный контроль. Отдельная проверка ошибочной версии требует именно version-error. Полный Linux/macOS CI нового commit должен пройти отдельно; старый PASS автоматически не переносится.

Подробности, hash входного отчёта и критерии: [Bundle ID regression](TEST_RECORDS/COLLECTOR-BUNDLE-ID-2026-09-28.md). История первого отказа без metadata: [Discovery failure](TEST_RECORDS/COLLECTOR-DISCOVERY-FAILURE-2026-09-28.md).

## Следующий шаг и открытые проверки

Нужен отчёт исправленного read-only сборщика с выбранной установленной AE 25.6, уже содержащий реальные модули. Далее — анализ symbols/strings/связей функций, AE-specific положительный контроль и проверка полных native/script/plugin origins, post-commit delivery, пропусков/дубликатов, стабильности и нагрузки. Только после конкретного кандидата — отдельный diagnostic probe. В текущем отчёте модулей и notification evidence нет.

Сборщик ничего не устанавливает, не запускает AE/отладчик и не меняет проекты/plugins/preferences/security; инструменты не входят в CEP-пакет. Инструкция: ../research/ae-notifications/README.txt.

Остаются адаптация donor installer/runtime/performance harness, полноценный editing UI/gestures, subframe timing, реальная совместимость Windows/Intel и signing/release. Детали: DONOR_INTEGRATION.md и research/ae-notifications/coverage.json. Main, пользовательская установка и продуктовый release этим этапом не затрагиваются.
