# Target Matrix

## Purpose

Этот документ отделяет заявленную цель от реально проверенной совместимости. Отсутствие проверки не считается поддержкой.

## Current development baseline

| Component | Configuration | Status | Evidence / limitation |
| --- | --- | --- | --- |
| Timeline Core | Node.js `v24.13.1`, TypeScript toolchain, macOS development host | **PASS** | Build и 13 pure Core/FakeHostAdapter tests PASS; это не проверка After Effects |
| After Effects host | AE 25.6.0.101, macOS 26.6.2 | **PASS (limited smoke)** | Panel open/read/refresh подтверждены пользователем; см. runtime evidence ниже |
| CEP | Bundled CEPHtmlEngine 12.0.1.2 | **PASS (limited smoke)** | Открытие панели, read/refresh и docking; restart/save/reopen ещё не проверены |
| ExtendScript | AE 25.6 host | **PASS (read smoke only)** | Snapshot read через CEP; editing/Undo и полная точность snapshot не проверены |
| UXP | Future adapter | **UNTESTED** | Не считается поддержанным без подтверждения AE-specific API |
| Windows | Not available in current environment | **BLOCKED** | Нужен Windows test host |
| Apple Silicon / Intel | Apple M1 Pro, 16 GB RAM / Intel unavailable | **PASS (M1 Pro limited smoke) / UNTESTED (Intel)** | Только open/read/refresh на M1 Pro |

Runtime evidence (2026-09-28): `docs/TEST_RECORDS/CEP-READ-REFRESH-AE25-2026-09-28.md`. Installed Build ID: `fstr-cep-aaa6da96ab91`; runtime identity independently unverified. Успешный smoke test не закрывает полный compatibility gate.

Дополнительный screenshot smoke (2026-09-28): последовательные слои на одной дорожке и docking — PASS. Evidence: `docs/TEST_RECORDS/CEP-PACKING-AE25-2026-09-28.md`, тот же установленный artifact.

## Required before CEP milestone

Перед первым CEP artifact нужно зафиксировать:

- минимальную и целевую версию After Effects;
- поддерживаемые macOS/Windows версии;
- Apple Silicon/Intel scope;
- CEP runtime и способ установки;
- доступность `Layer.id` в минимальной AE версии;
- test project и чистую процедуру установки;
- способ подтверждения реально загруженного Build ID.

Исследованные источники для CEP boundary:

- Adobe CEP 12 HTML Extension Cookbook: `CSInterface.evalScript()` выполняется асинхронно, ExtendScript работает в host main thread;
- Adobe After Effects Scripting Guide — `Layer.id` и `Project.layerByID()` добавлены в After Effects 22.0;
- Adobe CEP Resources / Samples — manifest, `CSInterface.js` и рекомендованное разделение `client`/`host`.

До этой фиксации проект не заявляет host compatibility и не считает CEP PoC production-ready.
