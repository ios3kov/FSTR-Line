# FSTR Line — текущий статус разработки

Дата: 2026-09-28  
Целевая среда: After Effects 25.6.0.101 / CEP 12 / macOS Apple Silicon

## Краткий итог

FSTR Line умеет читать состояние активной композиции, отображать его в панели
и выполнять базовые операции редактирования через After Effects. Полная
автоматическая синхронизация панели с изменениями в native Timeline пока не
реализована: поддерживаемый полный источник push-уведомлений не найден.

## Что готово

- versioned normalized snapshot contract;
- преобразование времени в целые кадры;
- deterministic track packing с сохранением AE Z-order;
- semantic move/trim/switch/select commands;
- snapshot/revision guards и stale-command rejection;
- FakeHostAdapter и pure Core fixtures;
- lifecycle controller панели: no-composition/loading/ready/refreshing/error;
- refresh coalescing и invalidation устаревших запросов;
- сохранение последнего корректного projection при ошибке refresh;
- CEP read/refresh PoC и базовый runtime lifecycle;
- экспериментальный Auto Sync через polling, выключен по умолчанию.

Локальная регрессия Core/CEP на предыдущих этапах проходила: до 45 тестов
PASS в зависимости от этапа. Эти тесты подтверждают Core, transport и
read/refresh поведение, но не закрывают SYNC-001.

## Что проверено по синхронизации

Проверены публичные источники событий After Effects 25.6:

- AEGP command/menu/idle hooks;
- `AEGP_Command_ALL`;
- render timestamps и render callbacks;
- `PF_AdvItemSuite1`;
- effect/UI callbacks;
- import/AEIO callbacks;
- render queue monitor;
- CEP CSEvent/PlugPlug;
- ExtendScript `Project.revision`;
- PICA/SP/ADM-related APIs.

`AEGP_Command_ALL` был проверен отдельным native probe. Probe загрузился в AE
25.6, но проверенная ExtendScript-операция создания composition/layer и
изменения их состояния не вызвала command callback. Это не подтверждает его
как полный источник уведомлений.

Обнаруженный `AEGP_RegisterListener` относится только к
`AEGP_RenderQueueMonitorSuite1` и сообщает о render jobs, frames и output
modules. Он не сообщает об изменениях Timeline.

## Текущий блокер

**SYNC-001 — BLOCKED.**

Требование: панель должна получать прямые уведомления AE об изменениях,
сделанных через native UI, ExtendScript и другие plugins, включая:

- move/trim/start/in/out;
- добавление, удаление и порядок слоёв;
- selection и switches;
- смену composition/project;
- playhead;
- Undo/Redo.

Polling, `Project.revision`, idle-проверки и события, которые отправляет сама
FSTR Line, не считаются выполнением этого требования.

## Что не следует считать готовым

- Полной event-based synchronization нет.
- Runtime coverage для всех native Timeline сценариев не доказана.
- Auto Sync не является финальным решением SYNC-001.
- Private или reverse-engineered hook ещё не найден, не проверен и не внедрён.
- Нельзя заявлять production-ready direct synchronization.

## Следующий этап

Отдельно запланировано исследование внутреннего поведения AE 25.6:

1. зафиксировать identity и hash бинарника AE;
2. искать строки, символы и dispatch-пути, связанные с project/Timeline;
3. наблюдать вызовы debugger/read-only tracing на изолированном тестовом
   проекте;
4. проверить native UI, playhead, selection, project changes, Undo/Redo,
   ExtendScript и plugin-originated edits;
5. при наличии конкретного кандидата создать отдельный diagnostic probe;
6. принять кандидат только после полной coverage matrix, проверки restart,
   пропусков/дубликатов, стабильности и влияния на производительность.

Этот этап является исследовательским. Наблюдение внутреннего вызова само по
себе не закрывает SYNC-001 и не означает, что механизм можно использовать в
production.

## Основные документы и commits

- `docs/PRODUCTION_PLAN.md` — продуктовые требования и архитектура;
- `docs/EVENT_SYNC_RESEARCH.md` — research gate и критерии SYNC-001;
- `docs/TEST_RECORDS/FULL-PUBLIC-NOTIFICATION-AUDIT-2026-09-28.md` — полный
  аудит публичных категорий API;
- `docs/TEST_RECORDS/COMMAND-PROBE-RUNTIME-2026-09-28.md` — runtime evidence;
- `docs/TEST_RECORDS/INTERNAL-AE-RESEARCH-PLAN-2026-09-28.md` — план следующего
  этапа.

Последние commits:

```text
e7d38c0 Document internal AE notification research plan
4f3fa96 Complete public notification source audit
f8de508 Add command hook runtime probe
```

Рабочее дерево на момент создания этого статуса было чистым.
