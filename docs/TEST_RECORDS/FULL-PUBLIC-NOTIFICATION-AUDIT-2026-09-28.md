# Full public notification-source audit — 2026-09-28

Run: `FSTR-FULL-PUBLIC-NOTIFICATION-AUDIT-2026-09-28-01`

## Acceptance test

A candidate is acceptable for SYNC-001 only if it is a supported AE 25.6 API
that pushes notifications for the required state changes without a timer,
revision query, full snapshot polling, UI focus dependency, or interception of
only FSTR-originated commands. Required origins are native UI, ExtendScript,
and other plugins. Required state includes layer timing/add/delete/order,
selection, switches, active composition/project, playhead, and Undo/Redo.

## Public SDK categories checked

### AEGP registration and hooks

`AEGP_RegisterCommandHook` is the only general command candidate. It provides a
command ID and a handled flag, not a changed-object notification or post-commit
snapshot. Runtime probe `f8de508` loaded in AE 25.6, but the tested
ExtendScript composition/layer mutation produced no command callback. The
candidate therefore cannot satisfy the required matrix.

`AEGP_RegisterUpdateMenuHook` runs when menus are about to be drawn.
`AEGP_RegisterIdleHook` is an idle callback. `AEGP_RegisterDeathHook`, version,
about, and registration hooks are lifecycle facilities. None is a project
change subscription.

### Render and asynchronous callbacks

`AEGP_GetCurrentTimestamp` and `AEGP_HasItemChangedSinceTimestamp` are pull
queries for render/video invalidation. Async frame callbacks report completion
of frame requests. These do not report Timeline model changes, selection,
playhead, project switches, or Undo/Redo.

### Effect UI and effect callbacks

`PF_EventExtra` and `PF_Event_*` callbacks are delivered to an effect's own UI.
Effect parameter-change selectors concern the effect instance being processed.
They cannot observe arbitrary native Timeline operations or changes made by
scripts and other plugins.

### Import, AEIO, Artisan, and render-queue callbacks

Import callbacks are scoped to import-manager activity. AEIO callbacks report
operations for a registered file/project format. The only public
`AEGP_RegisterListener` found in the 25.6 headers belongs to
`AEGP_RenderQueueMonitorSuite1`; its function block reports render-job, item,
frame, and output-module activity. Artisan and render-queue callbacks report
renderer or queue activity. None is a general project mutation notification
source.

### PICA, SP, and ADM notification-looking APIs

`SPStartupNotifyProc`, `SPShutdownNotifyProc`, and `SPFilterEventProc` concern
plugin adapter startup/shutdown and adapter events. They do not expose AE
project or Timeline mutation payloads. `ADMNotifierSuite2` is referenced by a
suite handler, but the downloaded SDK contains no documented AE Timeline
registration surface for it. A generic UI notifier would not establish
script/plugin/Undo/Redo coverage.

### CEP and scripting

CEP CSEvent/PlugPlug is an event transport. ExtendScript exposes state queries
and `Project.revision`; it does not expose a native Timeline subscription.
Sending a CSEvent or polling `revision` does not create an AE-originated push
source.

## Result

**No complete public direct notification source was found for AE 25.6.** The
only general public hook, `AEGP_Command_ALL`, is semantically incomplete and
negative in the tested script-originated scenario. The remaining callbacks are
scoped to lifecycle, menus, idle, effects, imports, rendering, or queue
activity.

This is a documented limitation of the inspected supported public surface. It
is not proof that private Adobe internals or a future API do not exist. A
private reverse-engineered hook would not meet the supported-API requirement
and is not accepted as the product solution.

## Evidence

- official AE 25.6 SDK archive SHA-256:
  `e02fa2b488c3cceb238866b648eb9a2526d308a260744367915a2f173663c36c`;
- `docs/TEST_RECORDS/SDK-25.6-HEADER-AUDIT-2026-09-28.md`;
- `docs/TEST_RECORDS/DIRECT-NOTIFICATION-CANDIDATES-2026-09-28.md`;
- `docs/TEST_RECORDS/COMMAND-PROBE-RUNTIME-2026-09-28.md`;
- official/community guide pages linked from `docs/EVENT_SYNC_RESEARCH.md`;
- Adobe Community reports recommending IdleHook polling for project detection.

SYNC-001 remains blocked. No production synchronization claim follows from this
audit.
