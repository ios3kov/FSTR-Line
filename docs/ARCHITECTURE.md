# Architecture

## Goal

Сделать Premiere-like Track View для After Effects **как визуальный слой над обычными AE Layers**.

Главное правило:

> FSTR Line не владеет проектом. Проектом владеет After Effects.

---

## Source of Truth

Источник истины — активная AE Composition.

FSTR Line хранит только краткоживущее UI-состояние:

- zoom;
- scroll;
- выделение UI;
- вычисленный packing;
- временное состояние drag/trim.

Не хранить дубли:
- media;
- layer timing;
- effects;
- keyframes;
- renderer state.

---

## Data Flow

```text
After Effects
   ↓ snapshot
CEP/UXP HostAdapter
   ↓ normalized model
Timeline Core
   ↓
UI

UI gesture
   ↓ command
Timeline Core
   ↓ HostAdapter
After Effects
   ↓ result
targeted refresh
```

## Architectural Boundaries

Система состоит из трёх явно разделённых уровней:

```text
UI
  ↓ user intent / render projection
Timeline Core
  ↓ normalized snapshot / semantic command
Host Adapter
  ↓ validated host operation
After Effects
```

### UI

UI отвечает только за:

- отображение projection, полученной от Core;
- ввод pointer/keyboard-жестов;
- локальный drag/trim preview;
- передачу user intent в Core;
- отображение состояния операции и ошибки.

UI не обращается к `CSInterface`, `evalScript()`, ExtendScript, UXP API или файловой системе напрямую.

### Timeline Core

Core является детерминированным и платформонезависимым слоем. Он принимает normalized snapshot и user intent, а возвращает:

- новую UI projection;
- semantic command для Host Adapter;
- диагностируемую ошибку валидации, если intent недопустим.

Core не выполняет host calls, не создаёт Undo Group и не знает о CEP, UXP, DOM, Node.js или ExtendScript.

### Host Adapter

Host Adapter — единственная граница с After Effects. Он отвечает за:

- чтение snapshot активной композиции;
- проверку актуальности snapshot перед изменением;
- атомарное выполнение semantic command;
- одну Undo Group на одну пользовательскую операцию;
- возврат результата и причин отказа;
- targeted refresh после успешной операции.

Host Adapter не должен принимать произвольный JavaScript-код от UI. Команды передаются как ограниченные сериализуемые данные с известным типом и параметрами.

### Source of truth и UI projection

Нормализованный snapshot — read model текущей активной композиции. Packing, selection projection, geometry и drag preview являются производными данными и могут быть пересчитаны в любой момент.

Панель не пытается «выиграть» конфликт с AE. Если состояние изменилось извне во время операции, текущий preview инвалидируется, выполняется refresh, а пользователь получает понятный результат вместо применения устаревшего изменения.

---

## Modules

### /core

Платформонезависимая логика:

- `TimelineModel`
- `PackingEngine`
- `SnapEngine`
- `SelectionModel`
- `TimeScale`
- `Commands`

### /host

Контракт с After Effects:

- `HostAdapter`

### /host/cep

Текущая реализация:

- `CEPAdapter.ts`
- `host.jsx`

### /host/uxp

Будущая реализация:

- `UXPAdapter.ts`

### /ui

- Timeline
- Tracks
- Clips
- Ruler
- Playhead
- Track Controls

### /tests

Тесты должны быть разделены по границам:

- pure Core tests — без After Effects;
- Host Adapter contract tests — с FakeHostAdapter;
- CEP integration tests — на реальном ExtendScript/After Effects;
- UI tests — только для поведения представления и жестов.

Одна и та же fixture-модель должна использоваться в Core и FakeHostAdapter, чтобы mock не расходился с контрактом.

---

## Layer Identity

Основная привязка:
- `Layer.id` для AE 2022+.

Дополнительно snapshot может содержать:
- comp item id;
- layer index;
- source id;
- name.

Но имя/индекс не использовать как основной persistent key.

`Layer.id` уникален только в контексте проекта/композиции, поэтому snapshot должен хранить также идентификатор композиции и project context. После смены active comp все прежние layer references считаются недействительными.

Имя, индекс, source id и type используются для отображения, диагностики и проверки изменений. Индекс не является стабильным идентификатором: он может измениться после reorder.

## Normalized Snapshot

Snapshot должен содержать как минимум:

```text
compositionId
compositionName
frameRate
frameDuration
duration
currentTime
layers[]
revision
```

Каждый layer snapshot должен содержать:

```text
layerId
index
name
type
startTime
inPoint
outPoint
label
selected
enabled
solo
locked
audioEnabled
capabilities
```

`revision` — идентификатор состояния, достаточный для обнаружения изменения контекста или данных, на которых основана команда. Он не является второй базой данных и не обязан сохраняться между сессиями.

Snapshot должен быть версионируемым. Изменение формата требует обновления adapter contract и fixtures, а не неявной интерпретации старых полей.

---

## Packing Rules

1. Clip представляет ровно один AE Layer.
2. Непересекающиеся clips могут находиться на одном визуальном track.
3. Пересекающиеся clips не могут занимать один track.
4. При пересечениях визуальный vertical order должен соответствовать AE compositing order.
5. Packing ничего не записывает в AE сам по себе.
6. Открытие панели — read-only операция.

### Z-order invariant

Простого правила «первая свободная дорожка» недостаточно. Packing должен сохранять вертикальный порядок всех одновременно пересекающихся layers.

Для каждого pair of overlapping layers:

- определяется порядок по AE `Layer.index`;
- clip, соответствующий слою выше в compositing order, должен оставаться выше в FSTR Line;
- assigned track должен удовлетворять этому ограничению.

Рекомендуемая модель — граф ограничений и детерминированное назначение track через topological/longest-path calculation. При конфликтующих ограничениях алгоритм обязан вернуть диагностируемую ошибку, а не построить визуально неоднозначную схему.

Дорожки являются только визуальными рядами. Они не изменяют AE index, stacking order или timing.

Граничные правила должны быть определены явно:

- clips, которые соприкасаются в одной границе (`outPoint == inPoint`), не считаются пересекающимися;
- zero-duration и некорректные ranges не скрываются packing-алгоритмом и обрабатываются отдельным validation rule;
- отрицательное время и ranges за пределами comp duration не округляются молча;
- одинаковый вход должен давать одинаковый packing независимо от порядка обхода коллекции.

---

## Editing Rules

### Move

Изменяется нативный timing layer.

### Trim

Изменяются нативные `inPoint/outPoint`.

### Reorder

Используется нативное перемещение слоя в AE stack.

### Switches

Visibility / Solo / Lock / Audio управляют соответствующими свойствами AE Layer.

## Time Model

Внутри Core время представляется frame-safe координатами, а не накоплением floating-point seconds.

- все операции move/trim/snapping работают в целых frame/tick координатах;
- frame rate и frame duration берутся из snapshot композиции;
- conversion в AE seconds выполняется только на host boundary;
- одинаковое входное значение должно конвертироваться детерминированно;
- округление на границах операции является частью контракта и покрывается тестами.

Если конкретная возможность After Effects допускает sub-frame timing, это должно быть явно отражено в host contract. Нельзя незаметно терять sub-frame значение простым округлением к ближайшему кадру.

Drop-frame display, negative start time, non-integer frame rate и out-of-range values должны иметь отдельные fixtures и правила отображения.

## Semantic Commands and Guards

Core создаёт семантическую команду, а не host script:

```text
MoveLayers(layerIds, delta)
TrimLayerIn(layerId, newIn)
TrimLayerOut(layerId, newOut)
SetLayerSwitch(layerId, switch, value)
ReorderLayer(layerId, targetIndex)
SelectLayers(layerIds)
SetCurrentTime(time)
```

Команда содержит operation id, composition id и snapshot revision, на которых она была рассчитана. Host Adapter перед выполнением проверяет:

- active composition;
- наличие и identity layers;
- revision или эквивалентные preconditions;
- locked/capability ограничения;
- допустимость timing и target index.

При устаревшем snapshot команда отклоняется без частичного изменения проекта. Сначала выполняется refresh, затем Core может построить новую команду.

Multi-layer command предварительно валидируется целиком. Если вся операция не может быть применена, Host Adapter не начинает частичное изменение. Исключения и ранний выход не должны оставлять открытую Undo Group.

## Runtime State Machine

Lifecycle панели моделируется явными состояниями:

```text
NoComposition
  → Loading
  → Ready
  → Previewing
  → Committing
  → Refreshing
  → Ready
```

Ошибка возвращает систему в состояние с корректно инвалидированным preview. Смена композиции, закрытие проекта, внешнее изменение слоя или потеря host connection должны отменять Previewing/Committing, если операция ещё не подтверждена.

Нельзя полагаться на набор независимых флагов, допускающих противоречивые комбинации `loading/dragging/refreshing`.

---

## Performance Rules

Запрещено:
- full project polling каждые 100–200 ms;
- host call на каждый mousemove;
- DOM node на каждый невидимый clip в больших проектах.

Использовать:
- snapshot;
- diff/targeted refresh;
- локальный drag preview;
- commit on mouseup;
- virtualization;
- throttling только там, где подтверждена необходимость.

---

## Compatibility Strategy

### Current

CEP + ExtendScript.

### Future

UXP Adapter после появления достаточного AE-specific API.

Общий Core остаётся неизменным.

Общими между CEP и UXP являются domain model, packing, snapping, selection, time geometry, semantic commands и test fixtures. Runtime lifecycle, manifest, permissions, bridge, filesystem и UI integration могут быть различными.

UXP не считается поддержанным только на основании существования migration documentation. Перед реализацией UXP Adapter нужно отдельно подтвердить поддержку целевой версии AE и наличие каждого требуемого host API.

---

## Research References

- Adobe CEP Samples — After Effects panel / CSInterface bridge:
  https://github.com/Adobe-CEP/Samples
- After Effects Scripting Guide:
  https://ae-scripting.docsforadobe.dev/
- Layer object:
  https://ae-scripting.docsforadobe.dev/layer/layer/
- Adobe UXP migration guide:
  https://developer.adobe.com/uxp/migration-center/uxp-for-cep-devs/technical-migration-guide/
- Adobe announcement on UXP expansion / CEP retirement:
  https://blog.developer.adobe.com/en/publish/2026/09/investing-in-the-future-of-creative-cloud-extensibility-uxp-comes-to-our-flagship-applications

---

## Architectural Non-Goals

Не строить:
- “Premiere внутри AE”;
- отдельный NLE;
- второй layer database;
- собственный render graph;
- собственную media pipeline;
- отдельный project format.

FSTR Line должен оставаться лёгким альтернативным представлением существующего After Effects Timeline.
