# FSTR Line — текущий статус разработки

Обновлено: 2026-10-01. Ветка `integration/host-safety-notifications`, Draft PR #2.
Принято **0 из 5 фаз**. SYNC-001 не закрыт. Main/merge/deploy/release не затронуты.

## Текущий шаг — AEGP helper и автоматизированные no-LLDB runtime gates

Последний implementation HEAD этого шага: `0ff7476a6b95edaea2693f8740ddc6874c8b70df`; checkpoint: `6bef1e475ef944cdd471a84041d7d4035b732d8c`. Правила main перечитаны, blob `701a8c1ae3acb4dbfe1d7eda94acbf8095b88608`.
Архив SDK распакован и его реальные объявления использованы при компиляции.
SDK и ранее полученные библиотеки остаются вне Git/CI; повторно присылать их не нужно.

Добавлены вход AEGP, собственная команда Start/Stop, обработчики menu/idle/death
и чтение времени активного слоя через SDK. Настоящий source callback создаёт
pending; без события idle не читает проект. Повторные события объединяются,
ошибка чтения не запускает бесконечный повтор, событие во время чтения делает
снимок неподтверждённым. Указатели payload не читаются и не сохраняются.

Добавлена macOS-проверка уже загруженных BEE/AfterFXLib: точная версия, hash,
UUID, заголовки/код в памяти и принадлежность экспортов. Отсутствующая библиотека
не загружается. Частная подписка выключена в обычной сборке; исследовательское
включение отдельно разрешается при сборке. Неизвестный результат регистрации/удаления блокирует повторы. Модуль pin-ится только после точной проверки host identity непосредственно перед private Insert; default/отклонённый старт его не pin-ит. Ошибки до первого зарегистрированного host hook полностью освобождают локальный State. После возможной регистрации callback/refcon и код остаются resident. Окончательная безопасность lifecycle внутри AE пока не доказана.

Локальный SDK-control покрывает восемь fresh-process сценариев AEGP с настоящими SDK-объявлениями и собственным host-окружением; dispatcher проверяется в optimized и ASan/UBSan. Добавлены no-LLDB JSONL trace и fail-closed parser: disabled-start запрещает private activity, active proof требует регистрацию, минимум две последовательные stable observation, собственный Stop/Remove и чистый host exit. Для контролируемого прогона parser теперь принимает build-bound expected-state plan и требует точное число/порядок `layer id + offset/in/duration`; snapshot-read failure блокирует PASS. Это доказывает наблюдаемое состояние, но само по себе не доказывает origin действия. В bundle recipe добавлен подписываемый `FSTRChainProbeBuild.json` с commit/Build ID и явными `AEGP_load=NOT RUN`, `SYNC-001=NOT RUN`, `handoffApproved=false`.

Exact HEAD `21a2d05` прошёл Integration gate `36834338257` и Read-only module input `36834338195`. Notification research tools `36834338125` прошёл новый research unit regression и остальные ранние проверки, затем упал в старом LLDB `mac_runtime_attach_smoke`: owned fixture завершился `-9` после detach. Это тот же открытый класс Issue #3; он не чинится и не ретраится в этом этапе. Это Linux/hosted-macOS evidence, **не полная SDK macOS-сборка и не запуск AE**.

Готов рецепт clean macOS bundle build с PiPL, Build ID, embedded ownership receipt и проверкой подписи. Перед подписью exact `.rsrc` теперь обязательно проходит DeRez-проверку: один PiPL `16000`, `Kind=AEGP`, имя/категория и `CodeMacARM64=EntryPointFunc`; расхождение fail-closed блокирует artifact. Добавлен безопасный disabled-start runner и отдельный research-opt-in `run_script_origin.py`: он отказывается работать при уже запущенном AE или непустом/сохранённом startup-проекте, создаёт только собственную несохранённую test-comp, выполняет два script-origin timing edit, Undo/Redo, Stop/Remove и валидирует no-LLDB trace. При невозможности доказать ownership он не закрывает потенциально пользовательский проект. Исправлена safety-ошибка в regex определения уже запущенного AE; добавлен regression-test на реальный `.app/Contents/MacOS/After Effects` путь.

На `0ff7476a...` script-origin gate усилен: после каждого edit/Undo/Redo он отдельно читает фактический `layer id/startTime/inPoint/duration` через публичный ExtendScript и требует, чтобы AEGP trace содержал ровно ту же последовательность. Времена сравниваются как эквивалентные рациональные значения, а не по внутреннему масштабу `A_Time`. Поэтому четыре произвольных observation больше не могут дать PASS. Exact-commit CI: Integration gate `36843261930` PASS, Notification research tools `36843262065` PASS, Read-only module input `36843262009` PASS. Это всё ещё automated/model/hosted-macOS evidence, не реальный AE runtime.

Implementation HEAD `5c2ae201...`: Integration gate PASS (run 36839331202), macOS Research unit regression PASS в run 36839331191. На текущем build-hardening increment добавлена fail-closed проверка уже скомпилированного PiPL через DeRez и regression на неправильный Kind/name/entry/duplicate resource; exact-head CI фиксируется отдельно после push. Остальные legacy LLDB шаги этого workflow не используются как критерий нового gate и могут по-прежнему отражать открытый Issue #3. **Реальная SDK macOS-сборка и запуск этих gates в AE 25.6.0.101 всё ещё NOT RUN.**
[Реализация, точные проверки и ограничения](TEST_RECORDS/AEGP-SDK-BRIDGE-2026-10-01.md).

## Следующий шаг

Запустить сначала `run_disabled_start.py`, затем `run_script_origin.py` на авторизованном Apple Silicon Mac с exact AE 25.6.0.101 и предоставленным SDK. Первый gate подтверждает загрузку exact disabled build без private activity; второй — opt-in регистрацию, два script-origin изменения, Undo/Redo, собственный Stop/Remove и чистый exit без LLDB. После этого отдельно остаётся native-UI/plugin-origin/full-field coverage и performance. SDK больше не является отсутствующим входом; не хватает реального host-прогона. Исследовательский helper пользователю как продукт не передаётся.

Полная матрица SYNC-001, post-commit, проекты/контекст и performance не приняты.
#3 и прежние runtime FAIL остаются открытыми; доработка LLDB не является текущей целью.

## Сохранённая база

[Предыдущее ядро](TEST_RECORDS/CHAIN-PROBE-CORE-2026-09-30.md) не изменено.
[Найденная цепочка UI](TEST_RECORDS/BEE-CALLBACK-SOURCE-2026-09-30.md).
[Отказ от dirty-only](TEST_RECORDS/DIRECT-SOURCE-MODULE-REVIEW-2026-09-30.md).
Все исторические test records и исходные файлы сохранены.
