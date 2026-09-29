# Completion trace target preparation — 2026-09-29

Baseline: 2b6673b. Added completion_targets.json with eight exact-build arm64
locations: an activity-edge branch before NumSlots and a signal-call site
after its check, separately for command/group/Undo/Redo. Addresses derive from
the complete disassembly recorded in COMMAND-COMPLETION-MATRIX-2026-09-29.md.

Why two points: with no subscribers the edge can occur without signal
invocation. Even a hit at the invocation instruction precedes the call and
does not prove any subscriber callback ran or completed. The existing logger
keeps commitPhase UNKNOWN and isNotificationProven false; preserve that policy.

The target definition shares the pinned module hash/UUID and AE version with
the existing context probe. Two tests check identity consistency and separate,
unique, bounded edge/call definitions. These checks do not revalidate machine
instructions or substitute for exact-build runtime identity verification.

Verification: 102 research tests PASS locally on macOS arm64; documentation
and git diff checks PASS. No product source or installed component changed.

Runner status: NOT IMPLEMENTED for this target set. It is not wired into the
existing launcher because that launcher operates on the currently selected AE
process/project and has interactive/manual phases. Do not run it against
user-owned work as an implicit experiment. No AE attach or mutation occurred.

Next: implement an explicit opt-in disposable-session runner with test-project
identity, fresh run IDs, bounded capture, operation markers, independent state,
clean detach and no automatic restart of a user session. Test runner refusal
paths before any live run. Success/error/no-op, two edits per group and separate
groups need distinct windows. Runtime correlation and every shipping gate
remain NOT RUN; this is instrumentation preparation only.

## Read-only preflight follow-up

Baseline dfd5d21. Added completion_preflight.py: requires explicit --app and
positive --pid, macOS arm64, exact bundle identity, module SHA/UUID, and the
same unique selected AE PID before and after module verification. Emits JSON
only; never launches/attaches, runs JSX, restarts or writes a project. It does
not create an executable capture plan. Even PASS has attachAllowed=false,
projectOwnership=UNVERIFIED and loadedModuleIdentity=NOT VERIFIED.

Three tests cover successful mocked identity, PID mismatch/change, module
mismatch, invalid PID and platform refusal. All 105 research tests PASS locally.
Real negative control using the installed AE bundle and explicit PID 1 returned
BLOCKED/exit 2: no unique selected AE process was running. No process was
attached or launched. Positive real-session preflight remains NOT RUN.

Limitations: process start identity/PID reuse, loaded modules, test-project
ownership and opt-in scope still need verification at actual attach time.
No cached PASS can authorize a later attach. Next implement the owned session
lifecycle and operation driver; the capture runner remains NOT IMPLEMENTED.
