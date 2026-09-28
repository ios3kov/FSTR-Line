# Production Plan

## Current Development Status

**Priority gate: direct AE-originated Timeline notifications — BLOCKED pending verified API.** User rejected periodic full-layer reads as the final synchronization design. The official AE 25.6 SDK headers were inspected: command/menu/idle hooks and render-change queries exist, but no complete push notification API for the required Timeline state was found. Native runtime probe is therefore not applicable. See `docs/EVENT_SYNC_RESEARCH.md` and `docs/TEST_RECORDS/SDK-25.6-HEADER-AUDIT-2026-09-28.md`. Existing Auto Sync prototype is not acceptance evidence for this requirement. Next step: obtain an Adobe-supported notification mechanism or clarification; do not substitute polling.

**Milestone: CEP read/refresh PoC и panel lifecycle — implementation complete, local verification PASS.**

Реализованы без зависимости от After Effects:

- versioned normalized snapshot contract;
- integer-frame time conversion и half-open range overlap;
- deterministic packing с сохранением AE Z-order;
- semantic move/trim/switch/select commands;
- snapshot composition/revision guards;
- FakeHostAdapter для проверки preflight и stale-command rejection;
- pure Core test fixtures.
- explicit panel lifecycle controller with no-composition/loading/ready/refreshing/error states;
- refresh coalescing and invalidation of in-flight results;
- preservation of the last valid projection when refresh fails.

Evidence: `docs/TEST_RECORDS/CORE-2026-09-28.md`, `docs/TEST_RECORDS/CEP-POC-2026-09-28.md`.

В AE 25.6.0 (Build 101) пользователь подтвердил открытие панели, чтение композиции и Refresh после смены композиции/добавления слоя. Скриншот следующего теста подтверждает объединение двух последовательных слоёв в одну дорожку и docking. Evidence: `docs/TEST_RECORDS/CEP-READ-REFRESH-AE25-2026-09-28.md`, `docs/TEST_RECORDS/CEP-PACKING-AE25-2026-09-28.md`. Полный integration gate остаётся открытым: остальные packing-сценарии, точность полей snapshot, runtime Build ID, Undo Group и визуальное совпадение с native Timeline ещё не проверены.

Дополнительные smoke tests: пользователь подтвердил переход `2 layers, 1 tracks` → `2 layers, 2 tracks` после создания пересечения в native Timeline и Refresh, а затем сохранение counts и layer IDs после save/reopen и restart AE. Evidence: `docs/TEST_RECORDS/CEP-OVERLAP-AE25-2026-09-28.md`, `docs/TEST_RECORDS/CEP-RESTART-AE25-2026-09-28.md`. Следующий этап — диагностика runtime identity и проверка полей snapshot для закрытия read/refresh integration gate перед editing UI.

Diagnostics implementation: generated UI/host Build IDs, queued host identity query, mismatch/error display and read-only snapshot JSON. Local regression: 33 tests PASS. Runtime screenshot confirms MATCH for `fstr-cep-92fd5e97d2fa` and successful manual Refresh, but initial automatic read returned an empty host response (FAIL, unresolved). Exact native field comparison remains NOT RUN. Next priority: reproduce and diagnose initial-read failure. Evidence: `docs/TEST_RECORDS/CEP-DIAGNOSTICS-RUNTIME-2026-09-28.md`.

Empty-response recovery: bounded snapshot/identity retries and a 20-entry bridge attempt log implemented; 39 local tests PASS. Root cause remains unknown; new AE startup verification is required. This workaround does not close the initial-read failure gate. Retry policy and removal/review condition: `cep/README.md`.

Composition discovery update: typed NO_ACTIVE_COMP handling, bounded startup discovery and focus/visibility refresh implemented. 42 local tests PASS; new artifact runtime test pending. Previous artifact screenshot showed empty/empty/NO_ACTIVE_COMP then MATCH; user confirmed manual Refresh restored layers. This establishes transport recovery, not automatic composition discovery or the empty-response root cause.

Automatic composition discovery: пользователь подтвердил появление слоёв без Refresh после инструкции перезапуска/открытия композиции. Installed candidate `fstr-cep-3c6a6297b9b4`; MATCH этого запуска отдельно не подтверждён. Evidence: `docs/TEST_RECORDS/CEP-DISCOVERY-RUNTIME-2026-09-28.md`. Постоянная синхронизация и editing остаются следующим объёмом работ, не подтверждённым этим smoke test.

## 1. Product Definition

Auto Sync prototype: opt-in active-composition reads, 2 seconds after each completed read, hidden-panel suspension and error stop. 45 local tests PASS. Native edits → panel refresh requires runtime verification; large-project profiling and targeted/diff refresh remain pending. This is read-only AE → UI synchronization, not editing or full bidirectional sync. See `cep/README.md` for scope.

FSTR Line — альтернативное визуальное представление существующего After Effects Timeline.

Продукт **не должен**:
- заменять внутреннюю модель AE;
- хранить собственную копию проекта;
- создавать собственный монтажный движок;
- вмешиваться в renderer;
- требовать конвертации существующих проектов.

After Effects — единственный source of truth.

### Обязательное требование SYNC-001: прямое получение изменений

**«Наша панель тоже должна получать изменения напрямую».**

FSTR Line должна получать уведомления об изменениях от самого After Effects и автоматически обновлять своё представление. Пользователь не должен нажимать Refresh или переводить фокус в панель для синхронизации с native Timeline.

Критерии приёмки:

- Изменения timing (move/trim), добавление, удаление, порядок и выделение слоёв, переключатели, смена композиции/проекта и Undo/Redo отражаются автоматически по уведомлениям AE.
- Изменения от native UI, scripts и plugins входят в проверяемый scope; перемещение playhead также должно получать прямые уведомления.
- Чтение актуальных данных после уведомления допустимо; постоянный опрос слоёв, project revision или idle-проверки не считаются выполнением требования.
- При отсутствии изменений нет периодического чтения состояния проекта ради обнаружения изменений. Начальное чтение и явное восстановление соединения оцениваются отдельно и не заменяют подписку.
- Нет ощутимого ухудшения отзывчивости и воспроизведения AE; это подтверждается сравнительными замерами, а не обещанием нулевой нагрузки.
- Приёмка требует доказанного API-источника уведомлений и runtime-тестов в целевой версии AE.

Статус: **BLOCKED — источник полного набора уведомлений ещё не подтверждён**. Это обязательное продуктовое требование, а не утверждение о текущих возможностях. Ограничение API не отменяет его автоматически; изменение требования требует согласования с пользователем. Research и coverage matrix: `docs/EVENT_SYNC_RESEARCH.md`.

---

## 2. Technical Model

Каждый clip в панели — ссылка на настоящий AE Layer.

Минимальная модель слоя:

```text
id
index
name
inPoint
outPoint
startTime
label
selected
enabled
solo
locked
audioEnabled
type
```

Для AE 2022+ используется persistent `Layer.id`.

Панель только:
1. читает состояние активной композиции;
2. строит компактное визуальное представление;
3. переводит пользовательские жесты в обычные операции AE.

### Normalized snapshot

Панель получает snapshot активной композиции пакетно. Snapshot включает `compositionId`, параметры времени, `currentTime`, массив layer snapshots и `revision`.

`revision` используется для проверки, что команда рассчитана на всё ещё актуальное состояние. Snapshot является краткоживущим read model, а не второй копией проекта.

Каждый пользовательский intent проходит цепочку:

```text
snapshot + intent
    → Core validation
    → local preview
    → semantic command
    → Host preflight
    → one AE operation / one Undo Group
    → refresh
```

Если preconditions больше не выполняются, команда отклоняется без частичного применения.

---

## 3. Core Feature — Track Packing

Непересекающиеся во времени слои могут отображаться на одной визуальной дорожке.

Пример:

```text
Layer A: 0–4
Layer B: 4–8
Layer C: 8–12

V1 | A | B | C |
```

Пересекающиеся:

```text
Layer A: 0–8
Layer B: 4–10

V1 | AAAAAAAA
V2 |     BBBBBB
```

### Жёсткий invariant

Packing никогда не должен менять реальный порядок композиции.

Если два слоя пересекаются во времени, их визуальное положение обязано сохранять тот же compositing order, что и `Layer.index` в After Effects.

Алгоритм не должен зависеть от случайного порядка входной коллекции. Для проверки использовать staggered-overlap cases, где A пересекается с B, B пересекается с C, а A и C не пересекаются. Простое greedy-размещение не считается достаточным доказательством корректности.

---

## 4. Architecture

```text
┌─────────────────────────┐
│ Timeline UI             │
└────────────┬────────────┘
             │
┌────────────▼────────────┐
│ Timeline Core           │
│ packing                 │
│ snapping                │
│ selection               │
│ geometry                │
│ time conversion         │
│ commands                │
└────────────┬────────────┘
             │
         HostAdapter
        ↙           ↘
   CEP Adapter    UXP Adapter
      NOW           LATER
        ↓
  ExtendScript
        ↓
 After Effects
```

Core не должен импортировать:
- `CSInterface`;
- CEP filesystem;
- Node APIs;
- CEP events;
- Chromium-specific APIs.

---

## 5. HostAdapter Contract

```text
getActiveComp()
getLayers()

selectLayers()
moveLayer()
trimLayerIn()
trimLayerOut()

setLayerEnabled()
setLayerSolo()
setLayerLocked()
setLayerAudioEnabled()

reorderLayer()

getCurrentTime()
setCurrentTime()
```

Контракт должен также определять:

- normalized snapshot schema;
- `compositionId` и `revision`;
- semantic command types;
- preflight/validation result;
- structured operation result;
- коды ошибок для stale snapshot, missing layer, locked layer, wrong composition и host failure.

Adapter принимает сериализуемую команду с известным типом. UI не передаёт ExtendScript или произвольный код.

Для одной пользовательской операции adapter выполняет:

1. проверку composition и revision;
2. полную preflight-проверку всех targets;
3. одну Undo Group;
4. операцию или атомарный набор изменений;
5. структурированный результат;
6. targeted refresh.

CEP реализует контракт через ExtendScript / `evalScript()`.

После появления полноценного AE UXP API создаётся второй адаптер без переписывания Core.

---

## 6. Sync Strategy

Не делать постоянный агрессивный polling проекта.

Синхронизация:

```text
panel open
panel focus
active comp change
после нашей операции
manual refresh
→ sync
```

Во время drag:
- UI двигается локально;
- AE не вызывается на каждый mousemove;
- на mouseup выполняется одна операция;
- после неё — точечный refresh.

Live preview можно добавить позже с throttling.

### Invalidation rules

Во время preview snapshot становится недействительным при:

- смене active composition;
- удалении или reorder target layer;
- изменении timing/switches извне;
- lock target layer;
- закрытии проекта или потере host connection.

В этом случае commit не выполняется, preview сбрасывается, а интерфейс показывает refresh/conflict result.

---

## 7. Undo

Каждый пользовательский жест должен соответствовать одному Undo:

```javascript
app.beginUndoGroup("FSTR Line: Move Clip");
// operation
app.endUndoGroup();
```

Примеры:
- drag = один Undo;
- trim = один Undo;
- multi-move = один Undo.

Undo Group закрывается через `try/finally` после успешного открытия. Ошибка, ранний выход и отмена не должны оставлять незакрытую группу. Поведение при невозможности применить часть multi-layer операции определяется как failure до начала изменения; частичный silent success запрещён.

---

## 8. Phase 0 — Technical Proof of Concept

Создать минимальную dockable CEP-панель.

Должна уметь:
1. открыть активную Comp;
2. прочитать layers;
3. построить tracks;
4. автоматически упаковать непересекающиеся layers;
5. выбрать AE layer по клику;
6. move;
7. trim in/out;
8. Undo;
9. refresh состояния.

До UI polish сначала доказать работу pure Core на fixtures и FakeHostAdapter. Реальный AE smoke test обязателен для подтверждения host bridge, selection, move/trim и Undo; mock-тест не заменяет AE-проверку.

### Gate

Переход дальше только если:
- открытие панели не изменяет проект;
- timing frame-perfect;
- native Timeline и FSTR Line показывают одинаковые данные;
- Undo корректен;
- save/reopen не ломает связь;
- композиция визуально идентична до и после открытия панели.

---

## 9. Phase 1 — Packing Engine

Покрыть unit-тестами:

- sequential clips;
- overlaps;
- nested ranges;
- одинаковые In/Out;
- zero-gap;
- long layers;
- negative start;
- разные FPS;
- большое количество пересечений.
- staggered overlaps;
- stable/deterministic output при перестановке входного массива;
- цепочки ограничений A↔B↔C;
- zero-duration и out-of-comp ranges;
- одинаковые timestamps с разным AE Z-order.

Основной invariant:

> одновременно видимые слои всегда сохраняют исходный AE Z-order.

---

## 10. Phase 2 — Production UI

Добавить:

- Adobe-like dark UI;
- track headers;
- clip blocks;
- AE label colors;
- ruler;
- playhead;
- zoom;
- horizontal/vertical scroll;
- snapping;
- selection;
- Retina/HiDPI;
- docked/floating layouts.

UI должен быть максимально лёгким и не дублировать функции AE, которые не нужны для Track View.

---

## 11. Phase 3 — Editing

Реализовать последовательно:

1. Move
2. Trim In
3. Trim Out
4. Multi-select
5. Multi-move
6. Reorder
7. Visibility
8. Solo
9. Lock
10. Audio enable
11. Snapping
12. Duplicate
13. Delete

Каждая функция проходит отдельный regression test.

---

## 12. Phase 4 — Compatibility / Stress

Тестовые композиции:

```text
10 layers
50 layers
200 layers
500 layers
1000 layers
```

Типы:

- footage;
- still;
- text;
- shape;
- precomp;
- adjustment;
- null;
- audio;
- camera;
- light;
- 3D;
- track matte;
- shy;
- locked.

Для больших проектов UI обязан виртуализировать невидимые tracks/clips.

---

## 13. Timing Matrix

Проверять минимум:

- 23.976
- 24
- 25
- 29.97
- 30
- 50
- 59.94
- 60 fps

Все операции должны быть frame-safe.

Core использует integer frame/tick coordinates. Конвертация в seconds выполняется только на границе Host Adapter. Отдельно проверяются:

- negative start time;
- sub-frame values, если они разрешены целевой версией AE;
- округление in/out при move и trim;
- drop-frame отображение;
- сохранение frame identity после save/reopen.

---

## 14. Clean Validation Rule

Каждый новый build/test run выполняется как чистая установка:

1. удалить старый build;
2. удалить предыдущую test-версию расширения;
3. собрать только текущий commit;
4. установить только новый build;
5. запустить чистый AE;
6. открыть чистый test project;
7. выполнить тест;
8. сохранить build SHA и результат.

Старые bundles, caches и test artifacts не должны влиять на новый прогон.

---

## 15. UXP Migration

Стратегия:

```text
сейчас:
Timeline Core
      ↓
 CEP Adapter

позже:
Timeline Core
      ↓
 UXP Adapter
```

При миграции допускается замена:
- host bridge;
- manifest;
- permissions;
- части UI API.

Не должны переписываться:
- packing;
- snapping;
- selection model;
- timeline geometry;
- command model;
- test fixtures.

---

## 16. Definition of Done v1

v1 считается production-ready только когда:

1. открытие/закрытие панели не меняет `.aep`;
2. последовательные AE layers компактно собираются в tracks;
3. overlap всегда сохраняет AE stacking order;
4. move/trim дают тот же результат, что и native AE operations;
5. один gesture = один Undo;
6. native Timeline остаётся полностью рабочим;
7. проект можно продолжать без FSTR Line;
8. отсутствует собственная копия проекта;
9. Core не зависит от CEP;
10. миграция на UXP требует нового HostAdapter, а не переписывания продукта.
11. stale snapshot не приводит к применению операции к изменённому layer;
12. multi-layer операция либо проходит preflight целиком, либо не меняет проект;
13. packing детерминированно сохраняет порядок всех пересекающихся layers;
14. semantic commands и normalized snapshot имеют зафиксированный versioned contract;
15. ошибки host/API диагностируемы и не скрываются как успешная операция.

---

## 17. Stop Criteria

Разработка этапа блокируется, если обнаружено хотя бы одно:

- панель меняет визуальный результат композиции без команды пользователя;
- packing нарушает Z-order;
- frame drift;
- Undo нестабилен;
- save/reopen теряет соответствие layer ↔ clip;
- большие проекты требуют постоянного агрессивного polling;
- Core начинает зависеть от CEP-specific API.

Сначала устраняется архитектурная причина, затем работа продолжается.
