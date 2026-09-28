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

---

## Packing Rules

1. Clip представляет ровно один AE Layer.
2. Непересекающиеся clips могут находиться на одном визуальном track.
3. Пересекающиеся clips не могут занимать один track.
4. При пересечениях визуальный vertical order должен соответствовать AE compositing order.
5. Packing ничего не записывает в AE сам по себе.
6. Открытие панели — read-only операция.

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
