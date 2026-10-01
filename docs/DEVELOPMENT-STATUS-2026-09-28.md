# FSTR Line — текущий статус разработки

Обновлено: 2026-10-01. Ветка `integration/host-safety-notifications`, Draft PR #2.
Принято **0 из 5 фаз**. SYNC-001 не закрыт. Main/merge/deploy/release не затронуты.

## Текущий шаг — AEGP helper и no-LLDB evidence gate

Текущий проверенный HEAD: `21a2d0599d1bdbff6cc6d960a79bc9cf6e0de4d8`; checkpoint: `6bef1e475ef944cdd471a84041d7d4035b732d8c`. Правила main перечитаны, blob `701a8c1ae3acb4dbfe1d7eda94acbf8095b88608`.
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

Готов рецепт clean macOS bundle build с PiPL, Build ID, embedded ownership receipt и проверкой подписи; полная сборка с SDK на Mac, установка/загрузка и реальные события ещё NOT RUN.
[Реализация, точные проверки и ограничения](TEST_RECORDS/AEGP-SDK-BRIDGE-2026-10-01.md).

## Следующий шаг

Собрать AEGP с предоставленным SDK на Apple Silicon Mac, проверить выключенный
старт и точный кандидат, затем минимальную подписку на отдельном проекте без LLDB.
Подтвердить повторные изменения, сохранность цепочки AE и удаление только своего
подписчика. SDK больше не является отсутствующим входом; не хватает подтверждённой
полной Mac-сборки и реального host-прогона. Плагин пользователю не передаётся.

Полная матрица SYNC-001, post-commit, проекты/контекст и performance не приняты.
#3 и прежние runtime FAIL остаются открытыми; доработка LLDB не является текущей целью.

## Сохранённая база

[Предыдущее ядро](TEST_RECORDS/CHAIN-PROBE-CORE-2026-09-30.md) не изменено.
[Найденная цепочка UI](TEST_RECORDS/BEE-CALLBACK-SOURCE-2026-09-30.md).
[Отказ от dirty-only](TEST_RECORDS/DIRECT-SOURCE-MODULE-REVIEW-2026-09-30.md).
Все исторические test records и исходные файлы сохранены.
