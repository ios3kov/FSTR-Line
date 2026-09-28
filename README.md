# FSTR Line

**FSTR Line** — dockable-панель для Adobe After Effects, которая показывает обычные AE layers в компактном Premiere-подобном виде: несколько последовательных слоёв могут визуально располагаться на одной дорожке.

## Главный принцип

Проект **не заменяет Timeline After Effects и не создаёт новый монтажный движок**.

After Effects остаётся единственным источником истины:
- каждый клип панели соответствует реальному AE Layer;
- `inPoint`, `outPoint`, `startTime`, порядок слоёв и switches остаются нативными данными AE;
- панель меняет только отображение и выполняет обычные операции над существующими слоями;
- проект `.aep` должен оставаться полностью рабочим без панели.

## Цель v1

Сделать альтернативный Track View:

```text
AE Timeline

Layer 1  █████
Layer 2        █████
Layer 3              ████
Layer 4  ██████████████████

FSTR Line

V1 | █████ █████ ████
V2 | ██████████████████
```

## В v1

- автоматическая упаковка непересекающихся слоёв в общие дорожки;
- сохранение реального compositing/Z-order AE;
- выбор слоя;
- move;
- trim in/out;
- multi-select / multi-move;
- snapping;
- zoom / scroll;
- playhead;
- visibility / solo / lock / audio;
- Undo/Redo через стандартный AE undo stack.

## Не входит в v1

- собственный renderer;
- собственный project/media engine;
- копия Graph Editor;
- собственные keyframes/effects;
- Premiere transitions;
- waveform/thumbnails;
- multicam.

## Архитектура

```text
Timeline UI
    ↓
Timeline Core
    ↓
HostAdapter
   ↙     ↘
CEP       UXP
сейчас     позже
    ↓
After Effects
```

Core не должен зависеть от CEP. Это позволит заменить CEP Adapter на UXP Adapter без переписывания логики таймлайна.

## Документация

- [Production Plan](docs/PRODUCTION_PLAN.md)
- [Architecture](docs/ARCHITECTURE.md)

## Статус

**Этап 0: документация завершена; pure Timeline Core реализован и проверен локальными unit-тестами.**

Реализованы и проверены без After Effects:

- normalized composition/layer snapshot;
- integer-frame time model;
- deterministic packing с сохранением AE Z-order;
- semantic move/trim/switch commands;
- snapshot guards и stale-command rejection;
- FakeHostAdapter contract checks.

Следующий технический gate: dockable CEP-панель, которая читает активную композицию, упаковывает реальные AE layers в Premiere-like tracks и поддерживает move/trim/undo без изменения визуального результата композиции. Pure Core не является доказательством работы CEP или After Effects.
