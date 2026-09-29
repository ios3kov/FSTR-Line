# Runtime v5 result and v6 direct-candidate plan — 2026-09-29

Input: `FSTR-AE-Runtime-20260929T063746Z-2c5ff382a5e8.zip`, size 19,107 bytes, SHA-256 `888d47eadebf4c5ad8531d4ec4ed0e76c08e61a65764e1fd225707c8bc2390bd`. Exact build identity: clean commit `84bb1a08ff89762599b99d23a281214f927291e2`, Build ID `fstr-runtime-84bb1a08ff89`.

V5 result: PASS attach/setup/capture/clean detach. Trace has 177 candidate hits, 18 phase markers, capture-start/end, no capture-error and no capture-limit. All eight interactive user steps have exact `-start` / `-done` delimiters.

Strict within-window evidence from bounded stacks:
- `DoProcessProjectChanges(unsigned long long)` at BEE file address `0x7afa7c`: timing 19, selection 2, switch 6, Undo 4, Redo 4, playhead 32; zero in both idle windows.
- `BEE_ThreadedRenderUpdateQueue::Render_EndUndoGroup()` at `0x778c54`: timing 6, switch 4, playhead 22.
- `BEE_CmdSeekItemToTime(...)` at `0x626d58`: playhead 10 and no other tested action window.
- `BEEp_SetLayerSwitch` exact marker appears in switch window; `BEE_SelectLayer`/selection-path markers appear in selection window.
- `SetContentChanged` appears during timing and Undo/Redo in the currently instrumented path, but not every action.
- idle-control and idle-after windows contain zero candidate hits in this trace.

This makes `DoProcessProjectChanges` the strongest current common-path candidate for native UI project/timeline mutations. It is still not proven as a notification API, post-commit event, or complete source. Selection has fewer common-path hits than other operations and must remain separately checked.

Runtime v6 narrows breakpoints directly to:
- DoProcessProjectChanges `0x7afa7c`
- Render_EndUndoGroup `0x778c54`
- CmdSeekItemToTime `0x626d58`
- SetContentChanged / BEE_EndGroup as transaction/content comparators
- exact selection/switch/Undo/Redo markers only for ground-truth correlation.

The same proven parent-terminal Enter protocol is reused. Human steps: idle, timing, layer add, layer delete, layer reorder, selection, switch, Undo, Redo, active composition switch, playhead, idle. This tests whether the common path covers structural changes before any ExtendScript/origin work.

SYNC-001 remains NOT RUN. Post-commit state and native/ExtendScript/other-plugin origins remain separate required gates.
