# UI dispatch is not a commit barrier — 2026-09-29

Baseline: a60dfa7. Scope: read-only arm64 disassembly of the same AE
25.6.0.101 BEE.dylib identified in NATIVE-SUBSCRIPTION-LIFETIME-2026-09-29.md.
No AE process attached, no project modified, no native function invoked.
Goal: establish whether the dispatcher itself guarantees deferred/post-commit
delivery. Acceptance: inspect all dispatch branches and distinguish facts
from ordering assumptions. Real-AE runtime acceptance: NOT RUN.

## Reproduction and findings

Use `xcrun llvm-objdump --macho --arch=arm64 --disassemble --dis-symname`
with these exact symbols on the installed BEE.dylib:

- `__ZN11BEE_Project22NotifySafelyOnUIThreadERKN5boost8functionIFvPS_EEEb`
- `__ZN15BEE_UndoContext22OnUndoCommandCompletedEv`
- `__ZN15BEE_UndoContext24FinishCurrentTransactionEv`

NotifySafelyOnUIThread starts at unslid address `0x3a4d8c`:

1. Compares the supplied project to BEE_Globals::GetProject at `0x3a4dc8`.
   Mismatch reaches verification failure and exception construction/throw,
   not a general-purpose queue for arbitrary project pointers.
2. Tests CurrentThreadIsMainThread at `0x3a4dd0`. If true and the bool
   argument is false, it tail-calls the callback at `0x3a4e1c` directly.
3. Otherwise obtains GetRegisteredMainThread at `0x3a4e24`, builds a bound
   callback and invokes a virtual dispatch method at `0x3a4ebc`. Exact queue
   ordering, cancellation and drainage are not established by this body.

Previously inspected SetContentChanged passes false. Thus its main-thread
path can invoke the dirty callback before SetContentChanged returns. This
disproves a universal deferred-delivery assumption, not the ordering of every
specific caller's mutation. A main-thread callback is not a commit barrier.

OnUndoCommandCompleted at `0x649c6c` checks NumSlots for the signal at context
offset `0xd8` and invokes `Signal<void(BEE_UndoContext*)>` at `0x649c9c`.
This identifies the payload and emitter, not full Timeline coverage.
FinishCurrentTransaction at `0x64a0b0` clears the transaction pointer at
`+0x58` before virtual transaction calls. Its inspected body does not directly
call OnUndoCommandCompleted; virtual dispatch may contain further behavior.
Do not equate the two merely from their names.

## Decision and next gate

Static branch inspection: PASS. Post-commit shipping acceptance: NOT RUN.
Reject using UI dispatch alone as evidence of committed events. Do not set
the delivery contract's committed marker based only on thread identity.

Next inspect actual callers of OnUndoCommandCompleted and virtual transaction
completion, then correlate completion with independent state in a controlled
harness. Selection/playhead/non-Undo edits remain separate coverage obligations.
Private ABI, project lifetime, mismatch recovery and module drainage remain
open. No production source or artifact was changed; documentation consistency
and `git diff --check` are the applicable checks (rules section 9).
