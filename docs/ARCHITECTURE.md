# Architecture

## Goal

Сделать Premiere-like Track View для After Effects как лёгкий визуальный слой над обычными AE Layers.

> FSTR Line не владеет проектом. Проектом владеет After Effects.

---

## Source of Truth

Источник истины — активная AE Composition.

FSTR Line может хранить только краткоживущее UI-состояние:

- zoom;
- scroll;
- UI selection;
- вычисленный packing;
- временный drag/trim preview.

Не хранить отдельную копию:

- media;
- layer timing;
- effects;
- keyframes;
- renderer state.

---

## Current Data Flow

```text
After Effects
   ↓ snapshot via ExtendScript
host/cep/host.jsx
   ↓ JSON
host/cep/cep-adapter.js
   ↓ normalized model
core/timeline-core.js
   ↓
ui/panel.js

UI command
   ↓
CEP adapter
   ↓ evalScript()
host.jsx
   ↓ native AE property edit
After Effects
   ↓ fresh snapshot
UI
```

Открытие/refresh панели — read-only. Mutating host call выполняется только по явной edit-команде.

---

## Current Modules

### `core/timeline-core.js`

Платформонезависимый Core:

- seconds ↔ frames conversion;
- snapshot normalization;
- Z-order-safe track packing;
- packing invariant validation.

Core не импортирует CEP, Node или Adobe API.

### `host/cep/cep-adapter.js`

Browser-side HostAdapter boundary:

- `getSnapshot()`;
- `selectLayer()`;
- `moveLayerFrames()`;
- `trimLayerInFrames()`;
- `trimLayerOutFrames()`;
- validation до `evalScript()`;
- structured host-error propagation.

### `host/cep/host.jsx`

ExtendScript implementation:

- читает active Comp;
- ищет layer по persistent `Layer.id`;
- сериализует normalized snapshot;
- выполняет native selection/move/trim;
- группирует успешный edit в один AE Undo group.

### `ui/panel.js` / `ui/panel.css`

Текущий PoC UI:

- compact tracks;
- clip blocks;
- AE label colors;
- selected state;
- manual refresh;
- frame-step edit controls.

### `CSXS/manifest.xml`

- AEFT 22.0+;
- CSXS 11 minimum;
- dockable Panel;
- Node.js не включён;
- remote network access не включён.

### `vendor/`

Self-contained runtime dependencies:

- Adobe `CSInterface.js` from CEP 11 resources;
- ES3-compatible `json2.js`.

---

## Planned Modules — not implemented yet

Не считать существующим кодом до появления соответствующего этапа:

- SnapEngine;
- richer SelectionModel;
- timeline geometry / ruler;
- playhead;
- virtualization;
- multi-move command model;
- reorder/switch commands;
- UXP adapter.

---

## Layer Identity

Основная привязка для AE 22+:

- `Layer.id`.

Snapshot дополнительно содержит:

- comp item id;
- layer index;
- source id;
- name.

Имя и index не используются как persistent identity.

---

## Packing Invariant

1. Один clip = один AE Layer.
2. Непересекающиеся clips могут делить visual track.
3. Пересекающиеся clips не могут делить visual track.
4. Для каждой одновременно видимой пары vertical order обязан соответствовать AE `Layer.index`.
5. Packing ничего не записывает в AE.

Текущая реализация проходит deterministic regression + randomized invariant tests и benchmark до 1000 layers.

---

## Editing Rules

### Move

Изменяется native `startTime`. AE сам сдвигает layer timing относительно source.

### Trim In / Out

Изменяются native `inPoint` / `outPoint`.

### Undo

Одна успешная edit-команда = один:

```javascript
app.beginUndoGroup("FSTR Line: ...");
// one committed edit
app.endUndoGroup();
```

Validation выполняется до открытия Undo group, чтобы отклонённая операция не создавала пустой Undo.

---

## Sync Strategy

Сейчас реализовано:

```text
panel open
manual refresh
after our edit
→ full active-comp snapshot
```

Не реализовано ещё:

- active-comp event sync;
- focus sync;
- targeted diff refresh.

Запрещён aggressive polling.

Во время будущего drag:

- preview локальный;
- host не вызывается на каждый mousemove;
- commit на mouseup;
- затем refresh.

---

## Performance Strategy

Уже действует:

- no project polling;
- no host call per mousemove;
- measured Core benchmark;
- real-AE smoke captures host timings;
- 10/50/200/500/1000 layer host stress harness.

До production ещё требуется:

- real panel layout/profile;
- idle CPU;
- memory;
- RAM Preview comparison;
- render comparison;
- MFR validation;
- virtualization profile.

---

## Compatibility Strategy

### Current

CEP + ExtendScript.

- After Effects 22+;
- CSXS 11 compatibility floor.

### Future

UXP Adapter после появления достаточного AE-specific API.

Не должны переписываться:

- packing;
- frame conversion;
- validation;
- platform-independent tests.

---

## Clean Validation

Каждый реальный AE тест должен исходить из clean build:

1. deterministic package;
2. package hash verification;
3. stale FSTR Line bundle/cache cleanup;
4. clean AE session;
5. isolated smoke project;
6. structured result;
7. regression comparison.

См. [TESTING.md](TESTING.md).

---

## Research References

- Adobe CEP Samples: https://github.com/Adobe-CEP/Samples
- Adobe CEP Resources: https://github.com/Adobe-CEP/CEP-Resources
- After Effects Scripting Guide: https://ae-scripting.docsforadobe.dev/
- Adobe UXP migration guide: https://developer.adobe.com/uxp/migration-center/uxp-for-cep-devs/technical-migration-guide/

---

## Architectural Non-Goals

Не строить:

- «Premiere внутри AE»;
- отдельный NLE;
- второй layer database;
- собственный render graph;
- собственную media pipeline;
- отдельный project format.
