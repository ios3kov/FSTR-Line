# FSTR Line — текущий статус разработки

Дата: 2026-09-28. Рабочая ветка: integration/host-safety-notifications, Draft PR #2. Main не слит и не изменён.

## Продукт

Typed Core, versioned commands/guards, усиленный host, проверяемый CEP package и read-only visual clips существуют. Editing UI остаётся закрытым до реальной AE-проверки.

SYNC-001 остаётся обязательным: полный прямой поток AE-originated изменений для native UI, ExtendScript и других plugins, включая timing, layer add/delete/reorder, selection/switches, project/comp, playhead, Undo/Redo. Polling/revision/idle/focus/self-events не заменяют требование.

## Новое реальное статическое Evidence

Пользовательский отчёт FSTR-AE-Static-20260928T213703Z-cd1461c05b83.zip успешно идентифицировал AE 25.6.0.101 и прочитал 256 реальных Mach-O модулей. Все 256 прочитанных модулей PASS; общий сбор BLOCKED, потому что достигнут лимит модулей/времени/байтов, поэтому не считается полным сканированием приложения.

Главные leads:
- BEE.dylib: BEE_Layer::CmdPreParamChange, BEE_Layer::CmdParamChanged, BEEp_CLayerDispatcher, BEEp_CProjectDispatcher, BEE_Selection.
- AfterFXLib: dvacore::messaging::Signal с BEE_UndoContext, BEE_Selection, LifetimeObserverToken и ProjectSettingsChanged message.
- main executable: ProcessBeginEndNotificationRegistry — пока низкий приоритет для Timeline.

Это впервые реальные внутренние AE leads, но ещё НЕ найденный notification source. Имена/символы не доказывают направление вызова, post-commit семантику или coverage.

## Следующий gate

Добавлен отдельный focused static pass для точных BEE/AfterFXLib hashes/UUIDs из пользовательского отчёта. Он использует native nm и LLDB только как статический reader: не запускает и не attach-ится к AE. Цель — подтвердить symbol sections/addresses и disassembly конкретных BEE_Layer change functions, затем только при совпадении identities перейти к candidate-specific runtime tracing.

Полный runtime SYNC-001, производительность, стабильность и production suitability остаются NOT RUN. Детали: TEST_RECORDS/STATIC-CANDIDATES-2026-09-28.md.
