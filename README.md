# FSTR Line

Dockable-панель для Adobe After Effects: обычные AE layers отображаются в компактных Premiere-like дорожках. Последовательные непересекающиеся слои могут занимать один визуальный ряд; порядок пересекающихся слоёв сохраняет AE Z-order.

## Главный принцип

After Effects — единственный источник истины. Панель не заменяет native Timeline, renderer или монтажный движок и не хранит собственную копию проекта. Каждый clip соответствует настоящему AE Layer; .aep должен оставаться рабочим без панели.

## Текущий статус

Ветка integration/host-safety-notifications содержит typed Core, versioned commands/guards, усиленный host, read-only визуальные clips, проверяемую сборку и изолированные инструменты исследования уведомлений. Это технический прототип, не готовый редактор. Подробный актуальный статус и ограничения: [Development Status](docs/DEVELOPMENT-STATUS-2026-09-28.md).

**SYNC-001: полные прямые уведомления AE обязательны и пока не реализованы.** Polling, idle/revision-проверки и зависимость от фокуса не считаются выполнением. Private-hook research не запрещён правилами категорически, но требует изолированной проверки и отдельного решения перед production. Реальные внутренние кандидаты в текущей среде ещё не установлены.

## Архитектура

Timeline UI → platform-independent Timeline Core → HostAdapter → After Effects.
Сейчас CEP; будущий UXP Adapter возможен только при подтверждённых AE-specific API. Core не зависит от CEP/DOM/Node. UI не передаёт произвольный ExtendScript; только ограниченные semantic commands.

## Цель v1 (не перечень уже готовых функций)

Packing, native selection, move/trim, multi-select/move, snapping, zoom/scroll, playhead, visibility/solo/lock/audio, native Undo/Redo и полная прямая синхронизация. Собственный renderer/media engine, Graph Editor, waveform/thumbnails, multicam и Premiere transitions не входят в v1.

## Разработка

Node 22+, npm; дополнительные model/research tests используют Python 3.10+ и C++17 compiler. Команды сборки и проверки: [CEP developer guide](cep/README.md). Чистый генерируемый пакет — dist/cep; CI не заменяет обязательную проверку внутри целевого AE и не означает разрешение на release.

## Документы

- [Development Rules](DEVELOPMENT_RULES.md)
- [Production Plan](docs/PRODUCTION_PLAN.md) и [Architecture](docs/ARCHITECTURE.md)
- [Integration scope / gates](docs/INTEGRATION_PLAN_2026-09-28.md)
- [Donor inventory](docs/DONOR_INTEGRATION.md)
- [Isolated notification research](research/ae-notifications/README.md)

Исторические test records сохраняются. Исправление интерпретации command probe — отдельный [erratum](docs/TEST_RECORDS/COMMAND-PROBE-ERRATA-2026-09-28.md), а не переписывание старого результата.
