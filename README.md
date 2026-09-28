# FSTR Line

**FSTR Line** — dockable-панель для Adobe After Effects, которая показывает обычные AE layers в компактном Premiere-подобном Track View: непересекающиеся слои могут визуально располагаться на одной дорожке.

## Главный принцип

FSTR Line не заменяет Timeline After Effects и не создаёт отдельный монтажный движок.

After Effects остаётся единственным источником истины:

- каждый clip соответствует реальному AE Layer;
- timing, Z-order и switches остаются нативными данными AE;
- packing меняет только отображение;
- проект `.aep` остаётся обычным AE-проектом и не зависит от FSTR Line.

## Цель v1

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

## Уже реализовано в Phase 0 PoC

- dockable CEP panel для AE 22+;
- read-only snapshot активной композиции;
- persistent identity через `Layer.id`;
- Z-order-safe packing;
- выбор AE layer из панели;
- frame-step Move;
- Trim In / Trim Out;
- один native AE Undo group на успешную edit-операцию;
- explicit bridge errors;
- self-contained CEP package без Node/network permissions;
- clean macOS/Windows dev installer;
- deterministic package + SHA-256 manifest;
- unit/mock/contract tests;
- полный FPS timing matrix;
- Core benchmark 10–1000 layers;
- real-AE smoke/profiling harness для macOS.

## Ещё не считается подтверждённым

До перехода к следующим продуктовым фазам нужен реальный clean run внутри After Effects:

- dock/install;
- native Timeline ↔ FSTR Line equality;
- реальный Undo;
- save/reopen identity;
- host/UI profiling;
- compatibility matrix.

## В v1 позже

- drag move / trim;
- multi-select / multi-move;
- snapping;
- zoom / scroll;
- ruler / playhead;
- visibility / solo / lock / audio;
- reorder;
- virtualization для больших проектов.

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
HostAdapter boundary
    ↓
CEP Adapter → ExtendScript → After Effects

                 later
                   ↓
              UXP Adapter
```

Core не зависит от CEP. Миграция на UXP должна заменить host bridge, а не логику таймлайна.

## Проверки

```bash
npm run check
npm test
npm run benchmark:core
npm run package:dev
npm run verify:package
```

На macOS после всех статических/CI проверок:

```bash
npm run smoke:ae
```

## Документация

- [Development Rules](DEVELOPMENT_RULES.md)
- [Production Plan](docs/PRODUCTION_PLAN.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Build / Artifact Identity](docs/BUILD_IDENTITY.md)
- [Testing](docs/TESTING.md)
- [Performance](docs/PERFORMANCE.md)
- [Status](docs/STATUS.md)
- [Current Status](docs/STATUS.md)
- [Testing / Clean Validation](docs/TESTING.md)
- [Performance](docs/PERFORMANCE.md)
- [Compatibility](docs/COMPATIBILITY.md)

## Текущий статус

**Phase 0 Technical Proof of Concept реализован в ветке `feat/phase0-cep-poc` и проходит автоматический CI.**

Следующий обязательный gate — clean real-After-Effects runtime smoke + profiling. До его прохождения Phase 1/2/3 не считаются открытыми.
