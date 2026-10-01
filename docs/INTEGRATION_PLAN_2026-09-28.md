# Integration and direct-notification research

Date: 2026-09-28. Development baseline: main 15d995e5d27140690c1966f14b2aa0029989a072.
Donor branch: feat/phase0-cep-poc at 2cfb93fbb1ebc488ddf05471ab62b8d7606b68f5.
Work branch: integration/host-safety-notifications. No merge, release, installation or changes to main are authorized by this stage.

## Product requirement (unchanged)

SYNC-001 requires complete AE-originated notifications for native UI, scripts and other plugins: timing, layer add/delete/reorder, selection, switches, active composition/project, playhead, Undo and Redo. A combination of event channels is acceptable only if coverage is complete. Periodic snapshot/revision/idle checks, focus events and self-emitted FSTR events are not substitutes. Reading data in response to a genuine notification is allowed.

## Rules review

DEVELOPMENT_RULES.md at the baseline was reviewed. It contains no categorical ban on private-hook research. Sections 3, 4, 13-16, 20-22 and 26 require justified research, safe isolated execution, compatibility evidence, diagnostics and truthful acceptance. Earlier research documents' supported-API-only wording was a project decision, not a quotation of the development rules. This user-directed stage permits investigation of internal mechanisms; it does not approve shipping an unverified private hook or weakening SYNC-001.

## Scope and ordered gates

1. Establish CI on this main-based branch; preserve typed Core, versioned commands and guards. Import or adapt donor assets selectively, never bulk-merge incompatible host contracts. Record retained, adapted and deferred donor work.
2. Add self-contained JSON transport. Test the actual host source, not only precomputed bridge responses. Fix bounded target-scoped restoration, timing writes, stale project context and UI error projection. No host behavior is accepted solely because mocks pass.
3. Consolidate package verification and read-only visual tracks. Editing UI remains gated on actual AE timing/Undo/Redo and exception tests; do not expose unaccepted writes merely to make the panel look finished.
4. Prepare isolated internal-notification research. Identify exact AE binary/module hashes, inspect symbols/strings, trace only concrete candidates on a disposable project, establish positive controls and distinguish pre-change from post-change delivery. Do not fabricate a candidate, offsets, callbacks or a coverage PASS.
5. Evaluate candidates against every origin/state row, missed/duplicate events, restart, stability, idle and playback impact. No installation, project mutation, debugger attach, security-setting changes or native rewrites occur implicitly.

## Acceptance planned before implementation

Automated Level 1: TypeScript build, all existing tests, actual JSX execution in a fault-injecting model, JSON-absent test, native-like startTime side effects, target-only rollback and partial-failure reporting, stale-context rejection, UI stale projection, deterministic exact package manifest, bounded static-research tooling and parsers. Evidence must identify its commit and distinguish simulations from AE.

Level 2 (not waived): exact clean artifact installed in AE 25.6.0.101 / macOS Apple Silicon, runtime Build ID, timing matrix, true Undo/Redo, close/reopen/restart, user/native/script/plugin changes and performance. Windows/Intel remain unverified until tested.

Research acceptance: positive control of the measuring mechanism; exact build and module identity; independent action ground truth; event sequence/timestamps/thread/channel; post-commit evidence; coverage and negative controls; separate uninstrumented performance baseline. Debugger pauses/tracing overhead must not be represented as production latency.

## Initial limitations

The current execution container is Linux, with no installed AE. Direct network cloning failed; repository writes and CI use the authorized GitHub connector. A search of available Library metadata did not locate the AE executable/SDK archive. The current tools do not establish access to the user's Mac debugger. Native binary inspection and runtime tracing are BLOCKED pending that exact environment; code and offline verification can proceed. No claims of native runtime execution follow from CI.

## Rollback and handoff

All changes remain on the integration branch, in logical commits; main and donor PR #1 are preserved. No release artifact is handed off until its mandatory gate passes. Runtime failures remain visible. This is implementation/research preparation, not a production-ready synchronization release.
