# FSTR Line — текущий статус разработки

Дата: 2026-09-29. Ветка: integration/host-safety-notifications, Draft PR #2. Main не изменён.

## Evidence already observed

Real AE 25.6.0.101 evidence confirms native project-change coverage, ExtendScript origin, active-comp transitions, real state oracle, restart/reopen and script-origin post-processing after endUndoGroup.

## Other-plugin origin — provenance/direct overlap OBSERVED, independent before-state still pending

Real overlap report:
`FSTR-AE-PluginOrigin-20260929T085035Z-6fbcd36ebc06.zip`, SHA-256 `1a444be0e63bfa35e88c06732681d8edfb338d43f527a460ef318277f7b82225`.

The independent public-SDK AEGP helper mutation and direct internal observer now overlap correctly:
- helper mutation VIDEO_ACTIVE 0→1, status 0;
- layer-switch-internal: 2;
- after-ProcessFromRenderThread: 13;
- DoProcessProjectChanges return: 13;
- end-group: 4;
- render-end-undo-group: 2.

Nearest direct hits around helper mutationEnd include layer-switch +15.845 ms, downstream boundary +37.511 ms and function return +56.336 ms.

The remaining acceptance failure is only state-oracle precondition: the pre-run snapshot was `NO_ACTIVE_COMP`, so L1 before=0 was not independently observed. Post-run snapshot had Comp 2 / L1 enabled=1.

Observer now blocks before attach unless an active comp with readable L1 state is already present. Final state gate requires exact match of snapshot before/after to helper beforeVideoActive/afterVideoActive.

No helper rebuild/reinstall is required.

SYNC-001 remains NOT RUN / not accepted until one corrected preflight overlap run closes the independent state correlation, after which production performance/stability gates still require separate acceptance.
