# FSTR Line — текущий статус разработки

Обновлено: 2026-09-30. Ветка: integration/host-safety-notifications, Draft PR #2. Main не изменён.

## Текущий статус — получение реальных данных AE, 2026-09-30

Завершено 0 из 5 фаз. База: `95207b30620dd2639224d71f3c80eba74c058217`.
Правила `main` не изменились: blob `701a8c1ae3acb4dbfe1d7eda94acbf8095b88608`.
Сборщик очереди отсутствовал в диагностических ZIP CI; добавлена отдельная
упаковка из чистого commit, запускающий файл, проверка целостности до сбора
и единый `report.zip` с идентификатором исходников и контрольной суммой.
`queue_static.py` и точная политика Adobe-модулей не изменены.

Локально: 17 новых проверок — 16 PASS, компиляция AppleScript NOT RUN на Linux.
Исправлен обнаруженный тестом путь записи отчёта внутрь выбранной `.app`
при отказе на другой ОС. Отдельный macOS smoke проверяет именно ZIP CI,
его launcher и отказ на неподходящем приложении без запуска AE.
[Критерии, результаты и ограничения](TEST_RECORDS/QUEUE-DATA-HANDOFF-2026-09-30.md).
Полный CI и SHA-256 пакета должны относиться к точному содержащему commit;
итоговая запись проверки сохраняется в PR #2 и CI artifact, не в старом отчёте.

Следующий необходимый вход — реальный `report.zip` с Mac, где установлен
лицензированный AE 25.6.0.101. В текущей среде такого отчёта и доступа к Mac нет.
Без него дальнейшее исследование очереди/клона BLOCKED; дополнительные модели
не заменяют эти данные. SYNC-001 и приёмка продукта остаются NOT RUN.
Диагностический пакет не устанавливает плагин, не запускает AE, не читает
проекты и ничего не отправляет автоматически. Main/merge/deploy/release не затронуты.

## Предыдущий этап — выборочный разбор очереди, 2026-09-30

Завершено 0 из 5 фаз. База: `d497393ed2617b1c2721b3118618812c52f25071`.
Правила из `main` перечитаны; их blob `701a8c1ae3acb4dbfe1d7eda94acbf8095b88608`
совпадает с предыдущим этапом. Изменяется только исследовательский инструмент.

Сборщик теперь принимает до 12 дополнительных точных имён из перечня функций
очереди/контекста через `--inspect-symbol MODULE:SYMBOL`. Все семь исходных
функций сохраняются. До дизассемблирования проверяются оба модуля и наличие
всех запрошенных функций. Ошибка дополнительной функции блокирует весь отчёт,
а не выдаёт частичный сбор за PASS. Добавлены 13 проверок, включая отдельный
сквозной тест на собственных dylib с настоящими Apple-инструментами в macOS CI.

Локально: 36 тестов сборщика, 34 PASS, 2 Apple-tools проверки NOT RUN на Linux.
Полный regression/build/package выполняется GitHub Actions для точного commit;
результаты предыдущего SHA его не заменяют.
[Приёмка инструмента и воспроизведение](TEST_RECORDS/QUEUE-FOLLOWUP-SELECTION-2026-09-30.md).

Новых выводов о работе самого AE этот этап не даёт: точных Adobe-модулей и
AE-процесса в этой среде нет. SYNC-001 остаётся BLOCKED/NOT RUN. Следующий шаг —
получить реальный отчёт, выбрать из него звенья исполнения/опустошения очереди,
обновления клона и получения контекста, затем разобрать их этим режимом.
Нельзя подменять этот шаг дальнейшими mock-тестами или объявлять безопасный
внешний вызов найденным только по имени/видимости функции.

Main, production и проекты пользователя не изменяются. PR #2 остаётся Draft.

## Предыдущий этап — проверка очереди, 2026-09-30

Завершено 0 из 5 фаз. База этого шага: `9393e3c722dff6a74dba2fcd5fc73b831c682ffd`.
Перечитаны правила из `main` (`c69e3663de59dc44cbdef18042891f6dd1ce5ee6`).

Добавлен отдельный read-only сборщик `research/ae-notifications/queue_static.py`:
проверка точной сборки, arm64 UUID и SHA-256 обоих модулей; семь обязательных
тел функций; перечень найденных путей очереди/контекста и их видимости в nm.
Пустой, неполный или ошибочный вывод, несовпадение адреса, таймаут и изменение
модуля дают BLOCKED. Код Adobe не вызывается и не загружается.

Локально после исправления тестовой среды: 23 проверки, 22 PASS,
Apple-tools контроль NOT RUN на Linux.
Собственный arm64 Mach-O объект проверен настоящими clang/LLVM; это не тест AE.
Полные проверки ветки сохраняются в GitHub Actions для точного SHA этого
изменения, отдельно от исторических результатов ниже.
[План, ограничения и Evidence](TEST_RECORDS/QUEUE-CONTEXT-COLLECTOR-2026-09-30.md).
Первый Linux CI прошёл, macOS CI обнаружил несовпадение путей тестового
каталога `/var` и `/private/var`. Причина воспроизведена отдельным тестом,
fixture исправлена без ослабления проверок сборщика.
[Протокол исправления](TEST_RECORDS/QUEUE-FIXTURE-PATHS-2026-09-30.md).
Результаты первой ревизии не считаются проверкой следующего коммита.

SYNC-001 остаётся BLOCKED/NOT RUN. Порядок/поток очереди, соответствие клона
UI-проекту и безопасный внешний контракт регистрации пока не доказаны.
Следующий шаг — собрать вывод на точных лицензированных модулях AE 25.6.0.101,
разобрать найденные queue/clone lifecycle функции и подтвердить контракты
в изолированном AE. Ни polling, ни LLDB не заменяют production-доставку.

PR #2 остаётся Draft; main, проекты пользователя и production не изменяются.

## Предыдущая проверенная база на 2026-09-30

Последняя проверенная ревизия перед этим обновлением документации:
`04e61e30cf3af35a184dc7d9e00cccbdbb8802b5`. Все четыре проверки GitHub CI
(`verify` и `mac-research` для push/PR) завершились успешно; результат проверен
2026-09-30. Этот результат относится к указанной ревизии, а не к последующим
коммитам документации.

Текущий этап — фаза 0 из пяти фаз (0–4): техническое доказательство и приёмка
в реальном AE. Полная приёмка фазы 0 ещё не завершена. Общий процент выполнения
не измерен; наличие реализации последующих частей не означает закрытие фаз.

Последние завершённые работы:

- Исправлено повторное принятие старой сессии уведомлений после промежуточного
  подключения. Память истории ограничена 1024 принятыми ID на экземпляр.
  Проверено: 71 тест TypeScript, 38 проверок runtime/пакета, 113 исследовательских
  тестов; сборка CEP прошла. Подробности: [проверка повторных сессий](TEST_RECORDS/NOTIFICATION-SESSION-REPLAY-2026-09-29.md).
- В AE 25.6.0.101 отдельные чтения подтвердили состояние тестового слоя после
  grouped/separate/no-op/off/on, контролируемой ошибки и восстановления.
  Двойные события соответствовали двум адресам контекста на двух потоках.
  Отладчик отключён корректно. Повторно использована тестовая композиция;
  всего созданные ранее две композиции оставлены в проекте по последнему
  наблюдению 2026-09-29. [Протокол AE](TEST_RECORDS/COMPLETION-REAL-AE-2026-09-29.md).
- Найден штатный подписчик завершения команды: локальная регистрация в
  AfterFXLib, последующая постановка работы в очередь и выбор GetProjectClone
  при исполнении. Это статическое исследование; безопасность внешнего вызова
  и чтения UI-проекта не доказана. [Исследование подписчика](TEST_RECORDS/COMPLETION-NATIVE-CLIENT-2026-09-29.md).

Главный блокер — SYNC-001: безопасный механизм уведомлений для поставляемого
продукта ещё не выбран и не подключён к панели. LLDB подтверждает наблюдаемые
пути изменений, но не закрывает приёмку доставки. Остаются безопасная регистрация
и время жизни callback, порядок выполнения/выбор проекта, post-commit semantics,
пропуски/повторы/закрытая панель на реальном источнике, производительность без
отладчика и проверка совместимости, сопровождения и лицензирования.

Следующий шаг: установить порядок и поток выполнения очереди, связь клона с
UI-проектом и доступный внешний путь регистрации/получения контекста. Затем —
изолированный native harness при доказанных контрактах и полная runtime-проверка.

PR #2 остаётся Draft/unmerged. Merge, deploy и release не выполнялись.
FSTR Layer Groups и раскрытие существующих precomp остаются будущими задачами
после текущего плана, см. раздел 18 [плана разработки](PRODUCTION_PLAN.md).

## История этапов реализации и исследования

Ниже сохранены результаты отдельных этапов на дату их выполнения. Более ранние
формулировки NOT RUN/не реализовано не отменяют более поздние проверки выше.

Located a native completion subscriber in SamuraiUpdateParamsUI: it acquires
context through an internal effect/project chain, waits only while activity is
in progress, posts deferred work, then disconnects on its normal callback path.
Its Connect specialization is local in AfterFXLib, and queue absence can skip
posting. Queued execution selects GetProjectClone, so UI snapshot/API safety
cannot be inferred. Safe external registration/context and queue completion remain open.
See `docs/TEST_RECORDS/COMPLETION-NATIVE-CLIENT-2026-09-29.md`.

Read-side reconnect review found a replay bug: session IDs could be reused
after an intervening connection. The consumer now keeps bounded per-instance
history and refuses reuse/exhaustion. Baseline failure reproduced; 71 TypeScript,
38 runtime and 113 research tests PASS on the clean code commit. See
`docs/TEST_RECORDS/NOTIFICATION-SESSION-REPLAY-2026-09-29.md`.

Controlled real-AE exception test on the owned layer confirmed partial state
persists after `finally` closes its Undo group; a separate read showed false,
then recovery showed true. Observer/detach and 113 research tests PASS.
This narrow result does not prove native callback delivery. See
`docs/TEST_RECORDS/COMPLETION-REAL-AE-2026-09-29.md`.

Separate read-only JSX checks on a reused owned test comp confirm enabled
states true/true/true/false/true after grouped/separate/no-op/off/on actions.
Observer/detach and 113 research tests PASS; signal-call sites still have zero
hits without a subscriber. The read uses the same scripting API, so native
post-commit delivery and the SYNC-001 production gate remain unverified. See
`docs/TEST_RECORDS/COMPLETION-REAL-AE-2026-09-29.md`.

Follow-up completion trace `completion-gcokp48f` distinguishes two context
addresses on two threads: each contributes 1/2/1 grouped/separate/no-op edges.
No signal calls; observer/detach PASS, 110 research tests PASS. Context roles,
independent state oracle and shipping delivery remain unproven. See the
follow-up section in `docs/TEST_RECORDS/COMPLETION-REAL-AE-2026-09-29.md`.

First owned-comp real-AE completion trace executed with explicit user approval:
grouped/separate/no-op edge counts 2/4/2, zero signal-call hits, clean detach
PASS. Doubling/context identity and independent state remain unresolved.
See `docs/TEST_RECORDS/COMPLETION-REAL-AE-2026-09-29.md`.

Fixed diagnostic post-commit marker Undo cleanup after mutation exceptions.
Baseline failure reproduced; four actual-JSX VM harness tests and 105 research
tests PASS. Real-AE execution remains NOT RUN. See
`docs/TEST_RECORDS/POSTCOMMIT-MARKER-UNDO-2026-09-29.md`.

Read-only completion preflight now validates explicit PID and exact on-disk
AE/module identity without attach permission. 105 research tests PASS; real
no-process refusal returned BLOCKED. Capture runner and real event correlation
remain unimplemented/NOT RUN; see completion probe preparation record.

Prepared eight pinned completion trace targets distinguishing activity edges
from signal-call sites; 102 research tests PASS locally. No live runner or
subscription is enabled. See
`docs/TEST_RECORDS/COMPLETION-PROBE-PREPARATION-2026-09-29.md`.

Fixed deep-static diagnostic false-PASS handling: failed/limited tool analysis
now yields BLOCKED. Baseline reproduced; 100 research tests PASS locally.
See `docs/TEST_RECORDS/DEEP-STATIC-COMPLETENESS-2026-09-29.md`.

Command/group/Undo/Redo setters share completion on aggregate activity ending,
not on each layer mutation. The static matrix and next correlation scenarios
are in `docs/TEST_RECORDS/COMMAND-COMPLETION-MATRIX-2026-09-29.md`.
This does not close source coverage or post-commit acceptance.
An owned executable model now checks all 128 boolean transitions and grouped
traces; 98 research tests pass locally. This validates the model's consistency,
not event delivery in AE.

Undo completion producer located in SetExecutingUndo's activity transition.
Scoped teardown can reach it during exception cleanup, so completion must not
be treated as mutation success. Static evidence only:
`docs/TEST_RECORDS/UNDO-COMPLETION-PATH-2026-09-29.md`.

UI dispatch ordering research establishes an inline main-thread callback path,
so dispatch does not itself prove post-commit semantics. Undo-completed emitter
and payload are located, but caller ordering and coverage remain unproved.
See `docs/TEST_RECORDS/UI-DISPATCH-ORDER-2026-09-29.md`.

Phase accounting: the production plan defines five phases (0–4). Phase 0's
full real-AE acceptance gate remains open; later-phase implementation exists
but does not establish sequential phase completion. No measured overall
completion percentage is available; the conversational 60% estimate is not
acceptance evidence.

Dirty-source producer inspection now finds an equality guard in
SetContentChanged: repeated identical dirty values skip this signal dispatch.
This path alone is not a complete mutation notification source. See
`docs/TEST_RECORDS/DIRTY-SOURCE-LIMIT-2026-09-29.md`.

Native lifetime follow-up identifies copied callbacks surviving registration
removal; Disconnect is not a proven quiescence fence. An owned C++ control
passes ASan/UBSan, but is not an AE runtime test. See
`docs/TEST_RECORDS/NATIVE-SUBSCRIPTION-LIFETIME-2026-09-29.md`.

Native subscription triage now identifies real exported connect/listener
candidates, but private ABI, ownership and full Timeline coverage remain
unproved. See `docs/TEST_RECORDS/NATIVE-SUBSCRIPTION-ABI-2026-09-29.md`.
The CEP adapter now refuses overlapping calls after timeout until the original
callback arrives. Reproduced with three failing baseline tests and verified in
the adapter harness; real-AE timeout acceptance remains NOT RUN. See
`docs/TEST_RECORDS/CEP-TIMEOUT-GUARD-2026-09-29.md`.

Implemented an isolated read-side notification delivery state machine and
contract: `docs/NOTIFICATION_DELIVERY.md`. It validates exact compatibility
identity, serializes reads, coalesces bursts, suppresses obsolete replies,
reconciles observable sequence gaps and stops on errors/deadlines. No private
AE producer is installed or wired to the panel. The adapter's new
`readNotificationSnapshot()` method supplies host-completion settlement for
this controller; the ordinary UI read still rejects promptly at its deadline.

Verification and limitations: `docs/TEST_RECORDS/NOTIFICATION-DELIVERY-2026-09-29.md`.
Clean implementation commit `fcf1cacd5df5`: 62 unit/contract tests, 34 runtime
harness tests and package integrity PASS. Evidence:
`docs/TEST_RECORDS/NOTIFICATION-DELIVERY-CLEAN-2026-09-29.md`.
This stage does not close any real-AE shipping source/performance gate below.

## SYNC-001 research coverage

**Origins/coverage research: OBSERVED. Production integration: BLOCKED.**

Real AE 25.6.0.101 evidence now covers:
- native UI timing/add/delete/reorder/selection/layer switches/Undo/Redo/playhead;
- ExtendScript-origin changes before/after restart;
- active composition changes with independent state oracle;
- independent AEGP plugin-origin mutation with direct stack provenance;
- restart/reopen;
- script-origin post-endUndoGroup processing positive control.

Latest final plugin-origin report:
`FSTR-AE-PluginOrigin-20260929T090335Z-1a2a1e564b15.zip`, SHA-256 `dad9249991e0383b752c06cf960052fd5ca611c8ad47e9ae175d48abefcc4068`.

Acceptance facts:
- snapshot before L1 video active = 1;
- helper provenance = 1→0, status 0;
- snapshot after L1 video active = 0;
- exact state/helper correlation = PASS;
- BEEp_SetLayerSwitch = 2 hits;
- project-processing boundary = 3;
- DoProcessProjectChanges return = 3;
- clean detach = PASS;
- stack contains FSTRPluginOrigin → AEGPDriver → AfterFXLib → BEE.

The independent other-plugin origin research gate is therefore closed.

## What remains before SYNC-001 can be accepted

LLDB breakpoints are not a shipping mechanism. Production acceptance still requires:
1. a defined compatible/failure-safe internal delivery mechanism (or later supported Adobe API);
2. exact-build/version mismatch refusal and recovery behavior;
3. post-commit state-read semantics for the actual shipping mechanism across required change families;
4. duplicate/coalescing/missed-event behavior, rapid bursts, no-op/error/cancel and panel-closed cases;
5. uninstrumented CPU/memory/playback responsiveness comparison against baseline;
6. compatibility/safety/maintenance/licensing review before any private production integration.

Polling/revision/idle/focus/self-events remain non-compliant substitutes.

SYNC-001 remains NOT RUN as a production integration gate.

## После текущего плана

FSTR Layer Groups — идея раскрывающихся групп слоёв без precomp добавлена
в будущую разработку. Вернуться после завершения текущего плана; текущий
scope не расширяется. См. раздел 18 в `docs/PRODUCTION_PLAN.md`.

Туда же добавлено раскрытие существующих precomp в панели FSTR: сначала
просмотр и навигация, с визуальным отличием от организационных папок.
Редактирование вложенных слоёв — отдельный будущий scope.