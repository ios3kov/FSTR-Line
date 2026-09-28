# Direct notification source search — candidate audit

Run: `FSTR-DIRECT-NOTIFICATION-CANDIDATES-2026-09-28-01`

## Candidate A — `AEGP_RegisterCommandHook(..., AEGP_Command_ALL, ...)`

**Status: partial candidate, not a complete source.** The AE 25.6 header allows an AEGP to register a command hook for all commands. It receives a command ID before AE handles the command, plus `already_handledB`; it does not receive a post-commit notification, changed object IDs, or a snapshot/diff. Potential coverage is unknown for layer drag/trim, selection, composition activation, playhead, scripts/plugins, and Undo/Redo. It requires a target-host matrix probe before any acceptance claim.

## Candidate B — `AEGP_RegisterUpdateMenuHook`

**Status: rejected.** The header says it runs when menus are about to be drawn and is not specific to a menu. It is not a project or Timeline change stream.

## Candidate C — `AEGP_RegisterIdleHook`

**Status: rejected as a direct source.** It supplies an idle callback and sleep interval, but no changed-object payload. Reading layers, project revision, or timestamps from it is polling.

## Candidate D — `AEGP_GetCurrentTimestamp` / `AEGP_HasItemChangedSinceTimestamp`

**Status: rejected.** These Render Suite functions are synchronous queries for rendering/video changes. They do not notify a panel and do not cover selection, ordering, switches, audio, or playhead state.

## Candidate E — `PF_AdvItemSuite1`

**Status: rejected.** Despite historical guide wording about being notified of Timeline changes, the AE 25.6 suite contains only `PF_MoveTimeStep`, `PF_MoveTimeStepActiveItem`, `PF_TouchActiveItem`, `PF_ForceRerender`, and `PF_EffectIsActiveOrEnabled`. There is no registration function or inbound Timeline callback. `PF_TouchActiveItem` tells AE to update an item; it does not report a native edit to a plugin.

## Candidate F — ADM notifier

**Status: not established as an AE Timeline source.** `AEGP_SuiteHandler.h` references `ADMNotifierSuite2`, but the downloaded SDK contains no `ADMNotifier.h` or AE-specific notifier registration API. A generic UI notifier would not establish project mutation, script/plugin, or Undo/Redo coverage.

## Candidate G — CEP CSEvent / PlugPlug

**Status: transport only.** CEP can dispatch and receive named events, but the public CEP API does not make AE emit native Timeline events. An event sent by FSTR reports only FSTR's own operation.

## Candidate H — `AEGP_RenderQueueMonitorSuite1::AEGP_RegisterListener`

**Status: rejected.** The only public `AEGP_RegisterListener` found in the
AE 25.6 headers is scoped to the Render Queue Monitor Suite. Its callbacks
report render jobs, render-queue items, frames, and output-module activity.
It does not report project, comp, layer, selection, playhead, or Undo/Redo
changes.

## Current conclusion

No public, complete, push notification source for SYNC-001 was identified in AE 25.6. `AEGP_Command_ALL` remains the only plausible partial channel and requires an instrumented native probe. It cannot be combined with idle polling and still be called a full direct source.
