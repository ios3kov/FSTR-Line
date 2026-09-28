# Production Plan

## 1. Product Definition

FSTR Line — альтернативное визуальное представление существующего After Effects Timeline.

Продукт **не должен**:
- заменять внутреннюю модель AE;
- хранить собственную копию проекта;
- создавать собственный монтажный движок;
- вмешиваться в renderer;
- требовать конвертации существующих проектов.

After Effects — единственный source of truth.

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
