# Target Matrix

## Purpose

Этот документ отделяет заявленную цель от реально проверенной совместимости. Отсутствие проверки не считается поддержкой.

## Current development baseline

| Component | Configuration | Status | Evidence / limitation |
| --- | --- | --- | --- |
| Timeline Core | Node.js `v24.13.1`, TypeScript toolchain, macOS development host | **PASS** | Build и 13 pure Core/FakeHostAdapter tests PASS; это не проверка After Effects |
| After Effects host | Version not yet fixed | **UNTESTED** | Требуется зафиксировать целевую AE version matrix до CEP integration |
| CEP | Preliminary manifest/runtime declaration; real host not available | **UNTESTED** | Static package checks only; требуется реальный CEP runtime и AE smoke test |
| ExtendScript | Version/AE host not yet fixed | **UNTESTED** | Не подключён на этапе pure Core |
| UXP | Future adapter | **UNTESTED** | Не считается поддержанным без подтверждения AE-specific API |
| Windows | Not available in current environment | **BLOCKED** | Нужен Windows test host |
| Apple Silicon / Intel | Not recorded | **UNTESTED** | Требуется зафиксировать hardware и выполнить relevant smoke tests |

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
