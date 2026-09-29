# Command completion state matrix — 2026-09-29

Baseline: 8e8a1ab. Target: AE 25.6.0.101, macOS arm64, BEE.dylib identity
as recorded in NATIVE-SUBSCRIPTION-LIFETIME-2026-09-29.md. Static inspection
only; no attach, native invocation, installation or project mutation.

Goal: identify which command states produce the shared completion signal.
Acceptance: inspect complete setter bodies, map state bytes to named setters,
record suppression and avoid inferring runtime coverage from symbol names.

## Reproducible inspection

Use `xcrun llvm-objdump --macho --arch=arm64 --disassemble --dis-symname`
on the installed BEE.dylib with:

- `__ZN15BEE_UndoContext19SetExecutingCommandEb`
- `__ZN15BEE_UndoContext24SetExecutingCommandGroupEb`
- `__ZN15BEE_UndoContext16SetExecutingRedoEb`

Together with the previously inspected SetExecutingUndo, the state bytes map
to command `+0x66`, group `+0x67`, Undo `+0x68`, Redo `+0x69`.
These are exact-build observations, NOT ABI declarations for production code.

| Setter | Entry (unslid) | Completion signal invocation | Suppression |
| --- | --- | --- | --- |
| Command | `0x649b3c` | `0x649c10` | Combined activity does not transition to inactive |
| Group | `0x649cb0` | `0x649d84` | Command active, or combined activity stays active |
| Undo (previous record) | `0x649db0` | `0x649ea4` | Command/group active, or Undo/Redo activity stays active |
| Redo | `0x649ebc` | `0x649f88` | Command/group active, or Undo/Redo activity stays active |

All completion paths target the same context signal at `+0xd8`, with a
NumSlots check before invoking it. Starting paths use `+0xb8`. For boolean
inputs and stable state during the setter, these branches correspond to
transitions of aggregate command/group/Undo/Redo activity, not a per-layer
mutation count. Reentrant callback behavior requires separate verification.

Example inference: with group=true, toggling command true then false need not
emit completion; clearing the last active group can emit it. No-op commands
and error cleanup are not distinguished by the payload, which is a context
pointer rather than a success result. This is a control-flow inference, not
a real-AE observation of nested command counts.

## Decision and next experiment

Producer structure: static inspection PASS. Full SYNC-001 coverage and
shipping post-commit semantics: NOT RUN. Do not count suppressed inner events
as transport loss, or equate every completion to a successful mutation.

The next controlled correlation experiment must distinguish:

1. Two edits inside one group versus two separate groups.
2. Ordinary command, Undo and Redo.
3. No-op, rejected edit and error/partial-change cleanup.
4. Native UI, ExtendScript and independent plugin origins.
5. Selection/playhead/context changes outside these command states.

Record operation markers, actual callback counts, outer-operation return and
an independent final-state oracle. Observe dispatcher/project-processing order
too; aggregate inactivity does not prove downstream queues have drained.
First resolve safe context acquisition/subscription ABI and callback lifetime
for a disposable harness. Do not wire an unverified private subscriber into
the panel. If instrumentation is used, label its evidence research-only.

Verification: complete bounded function disassembly, cross-check against prior
Undo record, documentation review and `git diff --check`. Application build,
regression and profiling reruns are N/A for this documentation-only change
(rules section 9). Runtime acceptance and compatibility review remain open.
