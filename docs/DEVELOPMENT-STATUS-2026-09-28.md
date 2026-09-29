# FSTR Line — текущий статус разработки

Дата: 2026-09-29. Ветка: integration/host-safety-notifications, Draft PR #2. Main не изменён.

## Реальный Context probe

`FSTR-AE-Context-20260929T080541Z-208329837f6e.zip`, SHA-256 `780327bb9297f69dc4473f565e2f9c2895ab8fa53c4172234a3d8735c48ec1e7`, PASS attach/capture/clean detach на AE 25.6.0.101.

### Active comp — OBSERVED

State oracle реально показал `Comp 1 → Comp 2 → Comp 1`. В обоих switch windows сработали exact `CItem::DeactivateVOut()` и `CItem::ActivateVOut()` по одному разу. Это закрывает active-comp positive-control gate для exact target build.

### State oracle — OBSERVED

Owned-file snapshot работает на реальном AE и возвращает comp/layer/time/selection/layer state. Timing edit также независимо подтверждён snapshot diff.

### Project processing

0x7af9f4 = DoProcessProjectChanges entry; 0x7afa7c = after ProcessFromRenderThread boundary; 0x7b055c = return. Idle-control содержит фоновые cycles, поэтому эти точки нельзя трактовать как one-event-per-user-action notification.

### Post-commit — всё ещё UNPROVEN из-за tooling bug

Marker-script упал на `File.flush()`, которого нет в target ExtendScript File API. Marker rows отсутствуют; этот subgate не засчитан.

Bug исправлен: маркеры теперь накапливаются в памяти и записываются одним `open("w") / writeln / close`. Следующий probe сокращён до:
idle → automatic post-commit marker → idle.

Active-comp/timing заново не проверяются.

Other-plugin provenance остаётся открытым.

SYNC-001 остаётся NOT RUN / не принят.
