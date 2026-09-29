# FSTR Line — текущий статус разработки

Дата: 2026-09-29. Ветка: integration/host-safety-notifications, Draft PR #2. Main не изменён.

## Delivery implementation stage

Fixed deep-static diagnostic false-PASS handling: failed/limited tool analysis
now yields BLOCKED. Baseline reproduced; 100 research tests PASS locally.
See `docs/TEST_RECORDS/DEEP-STATIC-COMPLETENESS-2026-09-29.md`.

Command/group/Undo/Redo setters share completion on aggregate activity ending,
not on each layer mutation. The static matrix and next correlation scenarios
are in `docs/TEST_RECORDS/COMMAND-COMPLETION-MATRIX-2026-09-29.md`.
This does not close source coverage or post-commit acceptance.
An owned executable model now checks all 128 boolean transitions and grouped
traces; 98 research tests pass locally. This validates the model's consistency,
not event delivery in AE.

Undo completion producer located in SetExecutingUndo's activity transition.
Scoped teardown can reach it during exception cleanup, so completion must not
be treated as mutation success. Static evidence only:
`docs/TEST_RECORDS/UNDO-COMPLETION-PATH-2026-09-29.md`.

UI dispatch ordering research establishes an inline main-thread callback path,
so dispatch does not itself prove post-commit semantics. Undo-completed emitter
and payload are located, but caller ordering and coverage remain unproved.
See `docs/TEST_RECORDS/UI-DISPATCH-ORDER-2026-09-29.md`.

Phase accounting: the production plan defines five phases (0–4). Phase 0's
full real-AE acceptance gate remains open; later-phase implementation exists
but does not establish sequential phase completion. No measured overall
completion percentage is available; the conversational 60% estimate is not
acceptance evidence.

Dirty-source producer inspection now finds an equality guard in
SetContentChanged: repeated identical dirty values skip this signal dispatch.
This path alone is not a complete mutation notification source. See
`docs/TEST_RECORDS/DIRTY-SOURCE-LIMIT-2026-09-29.md`.

Native lifetime follow-up identifies copied callbacks surviving registration
removal; Disconnect is not a proven quiescence fence. An owned C++ control
passes ASan/UBSan, but is not an AE runtime test. See
`docs/TEST_RECORDS/NATIVE-SUBSCRIPTION-LIFETIME-2026-09-29.md`.

Native subscription triage now identifies real exported connect/listener
candidates, but private ABI, ownership and full Timeline coverage remain
unproved. See `docs/TEST_RECORDS/NATIVE-SUBSCRIPTION-ABI-2026-09-29.md`.
The CEP adapter now refuses overlapping calls after timeout until the original
callback arrives. Reproduced with three failing baseline tests and verified in
the adapter harness; real-AE timeout acceptance remains NOT RUN. See
`docs/TEST_RECORDS/CEP-TIMEOUT-GUARD-2026-09-29.md`.

Implemented an isolated read-side notification delivery state machine and
contract: `docs/NOTIFICATION_DELIVERY.md`. It validates exact compatibility
identity, serializes reads, coalesces bursts, suppresses obsolete replies,
reconciles observable sequence gaps and stops on errors/deadlines. No private
AE producer is installed or wired to the panel. The adapter's new
`readNotificationSnapshot()` method supplies host-completion settlement for
this controller; the ordinary UI read still rejects promptly at its deadline.

Verification and limitations: `docs/TEST_RECORDS/NOTIFICATION-DELIVERY-2026-09-29.md`.
Clean implementation commit `fcf1cacd5df5`: 62 unit/contract tests, 34 runtime
harness tests and package integrity PASS. Evidence:
`docs/TEST_RECORDS/NOTIFICATION-DELIVERY-CLEAN-2026-09-29.md`.
This stage does not close any real-AE shipping source/performance gate below.

## SYNC-001 research coverage

**Origins/coverage research: OBSERVED. Production integration: BLOCKED.**

Real AE 25.6.0.101 evidence now covers:
- native UI timing/add/delete/reorder/selection/layer switches/Undo/Redo/playhead;
- ExtendScript-origin changes before/after restart;
- active composition changes with independent state oracle;
- independent AEGP plugin-origin mutation with direct stack provenance;
- restart/reopen;
- script-origin post-endUndoGroup processing positive control.

Latest final plugin-origin report:
`FSTR-AE-PluginOrigin-20260929T090335Z-1a2a1e564b15.zip`, SHA-256 `dad9249991e0383b752c06cf960052fd5ca611c8ad47e9ae175d48abefcc4068`.

Acceptance facts:
- snapshot before L1 video active = 1;
- helper provenance = 1→0, status 0;
- snapshot after L1 video active = 0;
- exact state/helper correlation = PASS;
- BEEp_SetLayerSwitch = 2 hits;
- project-processing boundary = 3;
- DoProcessProjectChanges return = 3;
- clean detach = PASS;
- stack contains FSTRPluginOrigin → AEGPDriver → AfterFXLib → BEE.

The independent other-plugin origin research gate is therefore closed.

## What remains before SYNC-001 can be accepted

LLDB breakpoints are not a shipping mechanism. Production acceptance still requires:
1. a defined compatible/failure-safe internal delivery mechanism (or later supported Adobe API);
2. exact-build/version mismatch refusal and recovery behavior;
3. post-commit state-read semantics for the actual shipping mechanism across required change families;
4. duplicate/coalescing/missed-event behavior, rapid bursts, no-op/error/cancel and panel-closed cases;
5. uninstrumented CPU/memory/playback responsiveness comparison against baseline;
6. compatibility/safety/maintenance/licensing review before any private production integration.

Polling/revision/idle/focus/self-events remain non-compliant substitutes.

SYNC-001 remains NOT RUN as a production integration gate.

## После текущего плана

FSTR Layer Groups — идея раскрывающихся групп слоёв без precomp добавлена
в будущую разработку. Вернуться после завершения текущего плана; текущий
scope не расширяется. См. раздел 18 в `docs/PRODUCTION_PLAN.md`.

Туда же добавлено раскрытие существующих precomp в панели FSTR: сначала
просмотр и навигация, с визуальным отличием от организационных папок.
Редактирование вложенных слоёв — отдельный будущий scope.
