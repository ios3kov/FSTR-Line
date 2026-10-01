# First actual AE runtime candidate trace — 2026-09-28

Input: `FSTR-AE-Runtime-20260928T221042Z-f348ac55b6db.zip`, SHA-256 `569fd656d255a481c438fc934177f1ef6d83b80fbb6ffc5c58965b70949b2144`, 10,426 bytes. It contains summary.json, trace.jsonl and lldb-log.txt. Build identity is clean commit `039025fbed28518d8f8dc65d5843221ea816f6d2`, Build ID `fstr-runtime-039025fbed28`.

Runtime result: PASS, exact AE 25.6.0.101 metadata, attach completed, all declared breakpoint location counts were inside bounds, capture completed, and LLDB detached cleanly. There are 392 candidate-hit rows, 10 phase rows, one capture-start and one capture-end. No capture-error or capture-limit row. This is the first real AE runtime observation, but every hit remains `commitPhase=UNKNOWN` and `isNotificationProven=false`; SYNC-001 remains NOT RUN.

Observed exact useful hits:
- `BEE_Undo(BEE_UndoContext&)` at file address `0x645958`: 22 hits. It fires heavily during the layer-timing window (17 hits) and also around the delayed Undo/Redo actions, so it is not a unique user-Undo notification.
- `BEE_Redo(BEE_UndoContext&)` at `0x645f24`: 2 hits, both in the Redo window after the delayed Undo activity. Useful as a command-execution marker, not a general change source.
- `BEE_SelectLayer(...)` at `0x302a8`: 6 hits, concentrated around selection and related UI actions. Useful selection-path lead, not yet a post-change signal.
- `BEE_UndoContext::OnUndoCommandCompleted`, `BEE_CmdModifySelection`, and the project-settings post breakpoint: 0 hits in this action matrix.

Invalid broad breakpoint evidence:
- Breakpoint labels `param-changed` and `param-pre-change` each recorded 181 hits, but every hit resolved to the same BEE file address `0x5c70` with function name `boost::detail::sp_counted_impl_p<Simple_Workqueue_Client>::~sp_counted_impl_p()`, not a CmdParamChanged implementation. This confirms broad regex/nlist aliasing is unsuitable here. These breakpoints are removed.

Control windows: no meaningful BEE Undo/Redo/SelectLayer hits occurred during idle-control or idle-after. The fixed schedule was usable but human action latency caused some actions to spill into the next named window; version 2 widens action windows and requests exactly one action per phase.

Version-2 predeclared goal: use only exact module file-address breakpoints from the static report, removing broad regex ambiguity. Add exact `BEE_AVLayer::CmdParamChanged` for normal layer timing, Undo state-transition methods, concrete selection mutation functions, AfterFXLib `CLayerSelection::SetSelection`, and two RealtimeNeedle functions for playhead correlation. This is still observational only. Exact-address resolution is separately tested on an owned Mach-O before user handoff.

No private function is called; no target expression/project variable is read; no target memory is written. Polling/revision/idle/focus/self-events are not accepted as SYNC-001.
