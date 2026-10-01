# Dirty source producer limit — 2026-09-29

Scope: read-only static arm64 inspection, AE 25.6.0.101 BEE.dylib,
same binary identity as NATIVE-SUBSCRIPTION-LIFETIME-2026-09-29.md.
Baseline repository: a38fb28. No AE process attached; runtime NOT RUN.
Goal: locate a producer and test whether its control flow supports repeated
same-state changes. Acceptance: identify precise branches and distinguish
static findings from whole-source runtime coverage.

## Evidence

Reproduce using `xcrun llvm-objdump --macho --arch=arm64 --disassemble
--dis-symname __ZN11BEE_Project17SetContentChangedEb` on the installed
Contents/Frameworks/BEE.dylib. Addresses are unslid, not runtime pointers.

- SetContentChanged starts at `0x3a1e10`.
- `0x3a1e2c` reads the existing byte at project offset `0x110`.
- `0x3a1e30` compares it with the supplied bool; `0x3a1e34` branches
  to `0x3a1ea0` when equal, skipping signal dispatch construction.
- Otherwise it stores the new value and checks the signal's NumSlots.
- `0x3a1e4c`/`0x3a1e50` construct address `0x3a4b60`, the previously
  identified BroadcastDirtyState function, for an indirect callback.
- `0x3a1e74` calls NotifySafelyOnUIThread with that callback. The name
  alone is not proof of post-commit ordering, lifetime or thread guarantees.
- The later block separately compares byte `0x112`, updates panic-save
  state and may invoke another callback. It does not remove the earlier
  equality guard on this dirty-signal producer.

BEE_GetProjectDirty (`0x65efd8`) reads bytes `0x110` and `0x111`;
it is a state query, not a mutation sequence counter. Constructor inspection
confirms initialization of the signal at `+0x120`. A whole-binary direct
`b`/`bl` scan found no named BroadcastDirtyState calls; the address construction
above explains why direct-call-only searching is insufficient.

## Decision

Static control-flow finding: PASS. This producer dispatches on a bool
transition, not on every call with the same dirty value. Therefore this path
alone is rejected as evidence of complete SYNC-001 delivery for repeated edits.
This does not prove all producers are transition-only, nor that every real edit
calls this setter. Other producers and state resets still require investigation.

Next: inspect NotifySafelyOnUIThread and Undo-completed/project-processing
producers for sequencing and coverage. Do not substitute dirty-state polling.
Shipping implementation stays BLOCKED; real-AE repeated-edit, post-commit,
performance and unload acceptance remain NOT RUN.

Verification scope: bounded symbol disassembly and documentation consistency;
`git diff --check`. No production source/artifact changed, so application
regression and performance reruns are N/A for this documentation-only record
under DEVELOPMENT_RULES section 9, not newly claimed PASS.
