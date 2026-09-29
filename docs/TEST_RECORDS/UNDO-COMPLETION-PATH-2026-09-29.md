# Undo completion producer — 2026-09-29

Baseline: 8285095. Scope: static arm64 inspection of AE 25.6.0.101 BEE
and AfterFXLib, identities recorded in NATIVE-SUBSCRIPTION-LIFETIME-2026-09-29.md.
Goal: trace the completion signal's producer and distinguish completion from
successful mutation. No AE attach, API calls, installation or project changes.

## Reproduction

Use `xcrun llvm-objdump --macho --arch=arm64 --disassemble --dis-symname`
on BEE.dylib with:

- `__Z8BEE_UndoR15BEE_UndoContext`
- `__ZN19BEE_ScExecutingUndoD1Ev`
- `__ZN15BEE_UndoContext16SetExecutingUndoEb`
- `__ZN15BEE_UndoContext12UndoPreviousEv`

Whole-module direct `b`/`bl` searches for OnUndoCommandCompleted in BEE and
AfterFXLib returned no matches. This does not establish absence of emission:
the setter below directly invokes the same signal without calling that method.

## Observed control flow

All addresses are unslid disassembly addresses.

- BEE_Undo constructs BEE_ScExecutingUndo at `0x645984`.
- On its normal exit path, it calls that guard's destructor at `0x645b28`.
  Conditional WorkQueue_PostUndo (`0x645ae4`) and UndoRedoCallUI
  (`0x645b14`) precede that point on their applicable paths. Their names do
  not prove that downstream asynchronous work is drained.
- Exception-unwind paths also invoke the guard destructor, including
  `0x645ca0` and `0x645e24`, before resuming unwind.
- The guard destructor checks its saved state and context lifetime, then
  calls SetExecutingUndo(false) at `0x64ad2c` when applicable.
- SetExecutingUndo has early suppression branches at `0x649dcc` and
  `0x649dec`. Otherwise it compares old/new combined Undo/Redo activity,
  with a starting-signal path at context `+0xb8` and completion at `+0xd8`.
- The completion branch checks NumSlots at `0x649e90` and invokes the
  signal at `0x649ea4`. This is the same offset and payload family as
  GetUndoCommandCompletedSignal / OnUndoCommandCompleted.

## Interpretation and decision

The completion signal is reachable from scoped Undo-state teardown, including
error cleanup when the guard/state conditions permit. It is not, by itself,
proof of a successful mutation or rollback. This is a static reachability
finding, not a measured event count or real-AE error test.

Do not translate this signal directly into a successful committed event.
An adapter must establish outcome/state semantics and distinguish error,
cancel and no-op cases. Whether this can safely trigger reconciliation after
all relevant host processing remains unproved. No private ABI is called.

Static producer identification: PASS. Runtime post-commit, error/no-op and
coverage gates: NOT RUN. SYNC-001 shipping integration remains BLOCKED.
Next trace SetExecutingRedo and normal command-state producers, then design
a controlled correlation test covering success, error, no-op and non-Undo
changes; the signal cannot be assumed to cover selection/playhead edits.

Documentation-only verification: inspected complete listed function bodies,
reviewed conclusions against branch conditions, and ran `git diff --check`.
Application regression/build/performance reruns are N/A for this record under
DEVELOPMENT_RULES section 9; no new artifact or runtime PASS is claimed.
