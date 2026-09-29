# FSTR Line — текущий статус разработки

Дата: 2026-09-29. Ветка: integration/host-safety-notifications, Draft PR #2. Main не изменён.

## Final Matrix — проанализирован

Реальный `FSTR-AE-FinalMatrix-20260929T072338Z-2daebc3abe79.zip` (SHA-256 `12f0de676336fe2fc61dd6f8692b77d5d52e32cec67fef3c542009b58ad5d2d4`) полностью завершён на AE 25.6.0.101. Обе LLDB sessions PASS/clean detach; restart подтверждён сменой PID 80268 → 96103.

`DoProcessProjectChanges` напрямую наблюдался для native timing/add/delete/reorder/selection/switch/Undo/Redo/playhead и для ExtendScript до/после restart. В idle windows — 0. Это сильный common-path lead, но не production notification API и не one-event-per-change контракт.

Открытые доказательные долги:
- active composition switch: 0 candidate hits → отдельный direct channel нужен;
- post-commit: UNPROVEN; normal windows имеют последний ProcessProjectChanges после известных markers, но burst даёт контрпример;
- historical Final Matrix state snapshots невалидны: DoScriptFile возвращал 0 вместо JSX return string;
- other-plugin provenance не доказан;
- LLDB burst overhead 14.579x нельзя переносить на production performance.

## Deep Static

Commit `020673eb4763bb12035cb0c2e54e6d7d4f951b8a` добавил read-only exact-build Deep Static: SHA+UUID verification, bounded disassembly известных функций и symbol discovery для active-comp/composition/viewer activation. Push/PR Linux+macOS gates PASS; 78 research tests PASS; Deep Static owned-Mach-O smoke PASS.

Реальный Deep Static report на AE ещё нужен для конкретных active-comp symbols и downstream calls `DoProcessProjectChanges`.

## State oracle — implementation fixed, real AE validation pending

State oracle переведён с ошибочного JSX return-value на уникальный owned-file handoff:
- snapshot JSX пишет состояние в mode-0700 workspace;
- parent проверяет regular file, no symlink, owned path, <=64 KiB, non-empty;
- AppleScript stdout `0` больше не используется как state.

Это исправляет будущий post-action oracle, но не ретроактивно исторический Final Matrix. Post-commit остаётся UNPROVEN до узкого реального positive control после Deep Static leads.

Никакого broad matrix, polling substitute, merge/deploy или private production hook сейчас нет.

SYNC-001 остаётся NOT RUN / не принят.
