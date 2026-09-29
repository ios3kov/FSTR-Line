# Deep Static result and narrow context/post-processing probe — 2026-09-29

Input: `FSTR-AE-Deep-20260929T075012Z-33e1ea673c0b.zip`, 19,866 bytes, SHA-256 `1d5b9e6b6a8cadbe360c93d980caa5a4123bafd06a86d35e8e6fc3999b84998d`. Status PASS. Exact BEE and AfterFXLib SHA+UUID match the previously measured AE 25.6.0.101 identities.

## Important correction

Static LLDB resolved `DoProcessProjectChanges(unsigned long long)` entry at **BEE 0x7af9f4**. The runtime address previously labeled `process-project-changes`, **0x7afa7c**, is actually function offset +136 immediately after:

`BEE_ThreadedRenderUpdateQueue::ProcessFromRenderThread(unsigned long long)` at the call site `0x7afa78`.

The function has a single static `ret` at **0x7b055c**. Historical evidence at 0x7afa7c remains valid as an observed boundary, but documentation/labels must not call it the function entry.

The disassembly also shows project timestamp reads before and after render-thread processing; this supports treating 0x7afa7c as a post-render-thread-processing boundary only. It does not by itself prove project state is fully committed.

## Active-comp leads from real AfterFXLib

Concrete exact-build symbols:
- `CPanoProjComp::ReActivate(unsigned char)` — 0xadb24
- `CPanoProjComp::Activate()` — 0xae23c
- `CPanoProjComp::Deactivate()` — 0xae268
- `CPanoProjItem::ReActivate(unsigned char)` — 0x197d4c
- `CPanoProjItem::Activate()` — 0x197e58
- `CPanoProjItem::Deactivate()` — 0x197eb0
- `CItem::ActivateVOut()` — 0x167e9c
- `CItem::DeactivateVOut()` — 0x162934
- `ScActivateItemPanel::ScActivateItemPanel(...)` — 0x7166d8

Getter/query leads such as `CEggApp::GetCurrentCComposition` and `NIM_GetActiveItem` were found but are intentionally excluded from the first runtime positive control because query frequency/noise is unknown.

## Next gate

A narrow real-AE Context/PostCommit probe is justified. It does not repeat the broad Final Matrix. It observes:
- idle,
- active comp A→B,
- active comp B→A,
- one layer timing edit,
- one automatic ExtendScript marker scenario,
- idle.

Acceptance for active-comp requires both a real state-oracle comp-name transition and one or more exact activation/deactivation candidate hits in the same action window.

For post-processing timing, the probe instruments exact function entry 0x7af9f4, after-ProcessFromRenderThread boundary 0x7afa7c and unique function return 0x7b055c. A bundled script writes wall-clock markers before mutation, after mutation and after endUndoGroup. Evidence can show whether boundary/return occurred after the script's end-undo marker, but this remains tested-origin timing evidence rather than universal native post-commit proof.

SYNC-001 remains NOT RUN until this positive control is analyzed.
