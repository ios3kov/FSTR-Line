# Second actual AE runtime trace and v3 correlation plan — 2026-09-29

Input: `FSTR-AE-Runtime-20260929T060524Z-8f6562f3cc77.zip`, 3,946 bytes, SHA-256 `ff6cb21dcbc59c0d2dd0daea8105b0c9eae6c13ed0f56ad6c7a350f9e1748984`. Exact runtime-v2 build identity: clean commit `9fe548abf025a779a4eff87c7b038c3536c71936`, Build ID `fstr-runtime-9fe548abf025`.

Result: PASS attach / breakpoint setup / capture / clean detach. Exact-address resolution succeeded for all 15 declared locations. Trace contains 39 candidate hits, 10 phase markers, one capture-start and one capture-end, with no capture-error/limit.

Important limitation: all 39 hits occurred before the scheduled `native-selection` phase. The trace therefore cannot establish negative coverage for selection/switch/Undo/Redo/playhead actions. Either the human actions were performed before their printed phase markers or the candidates did not cover them. The next protocol removes this ambiguity with audible Russian phase announcements while AE can remain foregrounded.

Observed v2 hits:
- `BEE_Undo`: 10
- `BEE_UndoContext::SetExecutingUndo`: 10
- `CLayerSelection::SetSelection`: 6
- `BEE_Selection::Add`: 6
- `BEE_SelectLayer`: 3
- `BEE_Redo`: 2
- `BEE_UndoContext::SetExecutingRedo`: 2
- zero: Undo starting/completed, selection remove/remove-all/cache, AVLayer ParamChanged, both RealtimeNeedle functions.

The idle-control interval itself contained selection and Undo-path activity, proving those command-level functions are not sufficient direct notifications by themselves.

Additional already-collected static evidence is reused without another full scan:
- BEE transaction boundaries: FinishCurrentTransactionIfAny `0x6499e4`, FinishCurrentTransaction `0x64a0b0`, StartTransaction `0x64a180`, SetContentChanged `0x64a33c`.
- Undo-completion Signal operator `0x64a704`.
- End-group boundaries `0x6444ac` / `0x644568`, PushUndoTask `0x64503c`.
- switch mutation `BEEp_SetLayerSwitch` `0x2a3460`.
- native UI correlation markers in AfterFXLib: MoveLayerCB `0x4af88`, MoveTrimAndSlipLayerCB `0x4bbd4`, CComp_CB_S_DoLayerTimeCmd `0x6cf18`, SetLayerSwitchCB `0x41c6c`.

Runtime v3 keeps exact SHA/UUID/file-address pinning, adds bounded top-8 stack metadata (function/module UUID/module name/file address only; no variables), labels each breakpoint by role, and uses optional `/usr/bin/say` announcements outside the target process. No private target function is called and no project variable is evaluated/read. LLDB breakpoint implementation is debugger-controlled and may use platform breakpoint mechanisms; the claim is no deliberate target data/state writes by our callback/controller.

Goal: correlate UI action markers to deeper transaction/mutation boundaries and determine whether a small union of direct channels can cover native UI changes. This is still not post-commit proof and not SYNC-001.
