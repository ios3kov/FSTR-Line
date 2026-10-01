# PostCommit positive control — real AE 25.6.0.101 — 2026-09-29

Input: `FSTR-AE-Context-20260929T081250Z-b6f1f48ae274.zip`, 7,662 bytes, SHA-256 `8611ed24247122810d604710165b75ca32913473f38225e421c237fd327245b6`. Exact build `ca72819f927ef94001e72ec42487f434567e2c10`. Runtime observer PASS and clean-detached.

The corrected marker script produced:
- `before`: 1790669562027 ms, selected layer video enabled=1
- `after-mutation`: 1790669562130 ms, enabled=0
- `after-end-undo`: 1790669562156 ms, enabled=0

The independently written state snapshot after the action window also recorded the same selected layer with `enabled=0`, while pre-window snapshot recorded `enabled=1`.

Within the script-postcommit action window:
- first `after-process-from-render-thread` after the script's `after-end-undo` marker: **+46.631 ms**
- first `DoProcessProjectChanges` return after `after-end-undo`: **+75.062 ms**
- additional project-processing cycles continued later in the same window.

This closes the **script-origin post-processing positive control**: for the tested script mutation, the observed internal post-render-thread boundary and function return occur after `app.endUndoGroup()` has returned and after the script itself reads the changed layer flag.

This does **not** establish:
- a universal one-event-per-change contract;
- that every native UI mutation has identical ordering;
- a supported/stable private ABI;
- production performance.

Idle windows still contain occasional complete project-processing cycles, so these points are worker/wake boundaries and require event-driven coalescing/state read rather than treating each hit as one logical mutation.

Combined evidence now has:
- native structural/timing/selection/switch/Undo/Redo/playhead common path: OBSERVED
- ExtendScript origin: OBSERVED
- active composition direct channel: OBSERVED via CItem ActivateVOut/DeactivateVOut + state oracle
- state oracle: OBSERVED
- script-origin post-processing after endUndoGroup: OBSERVED
- restart/reopen: OBSERVED
- other-plugin provenance: still UNPROVEN.

Next gate is an independent diagnostic AEGP helper using only public SDK setters to create one plugin-origin layer switch while the observer is active.
