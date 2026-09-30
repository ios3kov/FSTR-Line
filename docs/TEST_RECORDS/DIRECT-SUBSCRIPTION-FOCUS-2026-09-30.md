# Direct subscription first — 2026-09-30

Baseline: `cabf37d11571722f8392035803bd06d7dd689508`.
Branch: `integration/host-safety-notifications`; PR #2 Draft/unmerged.
Phase 0: 0/5 phases accepted. Rules rechecked from main, blob
`701a8c1ae3acb4dbfe1d7eda94acbf8095b88608`. User requested effective progress on
actual notifications, not further general-purpose debugger work.

## Decision and evidence, not a new notification claim

Separate the **event source** from the **main-thread delivery mechanism**.
The existing BEE threaded render queue is neither a reliable receipt nor an
owned UI-project handle. Its cancellation/pre-enqueue rejection and clone
selection remain documented in [the received context report review](CONTEXT-TABLE-REAL-REVIEW-2026-09-30.md).
It is no longer the default transport for the minimal subscription proof.

The SDK guide documents `AEGP_CauseIdleRoutinesToBeCalled` as asynchronous and
callable off the main thread, provided its function pointer is acquired on the
main thread. It also describes AEGPs as resident for the AE session, unlike
effect plug-ins. These are useful interface contracts, NOT a test of AE 25.6:

- https://ae-plugins.docsforadobe.dev/aegps/aegp-suites/#aegp_utilitysuite6
- https://ae-plugins.docsforadobe.dev/aegps/implementation/#threading
- https://ae-plugins.docsforadobe.dev/aegps/implementation/

Proposed proof path: actual AE-originated callback -> bounded pending state in a
resident AEGP -> cached `AEGP_CauseIdleRoutinesToBeCalled` pointer -> host idle
callback -> fresh public-API project/layer read. Idle is ONLY a dispatcher:
no source event means no project/revision/layer reads and no self-scheduling.
A wake request is not a delivery acknowledgement or post-commit barrier. A failed
wake/read retains pending work or an explicit error, never a fabricated success.
Latency, host shutdown, reentrancy, context changes and incomplete delivery must
still be measured/tested. Residency does not prove callback data ownership or
make arbitrary effects safe to unload. No native adapter is implemented here.

First source candidate is the already-located exported
`BEE_Project::ConnectDirtyStateChangedSignal`, not a newly discovered API.
[Its native client and lifetime](NATIVE-SUBSCRIPTION-LIFETIME-2026-09-29.md) give
concrete producer/ownership leads. Critical discriminator: **does a second edit
while already dirty still emit a usable event?** If it only signals the first
clean-to-dirty transition, reject it as the repeated-edit source immediately.
Then evaluate Undo-completion as a separate source, without assuming coverage
for selection/playhead/context or combining incomplete channels by assertion.

## Stop criteria before the next implementation

Use one narrow proof: native layer timing edit -> direct source callback ->
correct current-state read without LLDB. Include two consecutive edits without
saving, a script-origin edit, Undo/Redo, no-op/idle, project close/change and panel
close. An isolated owned project is mandatory; no automatic user-project edits.
This is a discriminator, not full SYNC-001 acceptance. All original required
origins/fields, lifecycle, load and compatibility gates remain after it.

Before calling private code, establish registration/return/callback ABI and
project/connection ownership from actual clients. No guessed prototype/layout,
address detour, process patch, sentinel effect or polling fallback. If the source
fails coverage or lacks a safe external contract, record rejection and change
source; do not add another generic collector or debugger workaround to this path.

## Missing input and one bounded handoff

This session has the verified `2mniyqyl` report and research packages, but no full
BEE/AfterFXLib/dvacore module bytes. The report SHA-256 remains
`01f05cb593648ba6fd60d044f4c765af0d21bf0a79729340deb41c5d66448d3a`.
A checked constructor body is merely a jump to another body, so another finite
list of eight functions risks repeating the same request cycle. Instead collect
three existing modules once, using their established paths in the lifetime record.

`Copy-Research-Modules.command` only streams those three files into a new private
ZIP. No Adobe or debugger invocation, symbol scan, installation, network upload,
project/preferences access, process signalling or deletion. It verifies source
hashes before/while/after copying and reads back ZIP payloads before success.
Missing/empty/nonregular/symlink inputs are refused. Each source is bounded to
1 GiB; output must be outside the application. Incomplete output remains partial,
not an accepted run. Before/after hashes do not claim an atomic filesystem snapshot.

The ZIP contains library bytes and a manifest, not licensed code to publish in
Git/CI. The user chooses whether to attach it here; upload is not automated.
The manifest deliberately does NOT claim version compatibility. On receipt compare
all three hashes with the established research baseline before interpreting ABI:

| Module | Expected SHA-256 |
| --- | --- |
| BEE.dylib | `817b9de9c6d57b5d6988b634842090e1528fe817a5685c8d1ff358553c6660ca` |
| AfterFXLib | `ce3aa2f16fe5449a77379a6b622e1a221596e511b86f7708dd3e2f7a3cced01a` |
| dvacore | `cb6faaf5b745903b80b44105b658ab68186d5065ae47c8a57c9b23e26aa8ecb0` |

## Acceptance defined for this separate data-copy artifact

Required: bash syntax and actual-launcher tests for byte/hash/member integrity,
unchanged originals, private permissions, repeat/no overwrite, missing/empty/FIFO/
symlink sources and application-internal output refusal. Run on Linux and macOS
owned files. This helper imports no FSTR research/runtime module. Its source hash
links the standalone artifact to the containing Git commit and manifest. No SDK,
LLDB or Adobe runtime is necessary to test file copying; no AE compatibility PASS
is inferred. The dedicated workflow checks this scope without changing any
existing workflow or converting its known FAIL into PASS.

Local source-subset result: 8/8 actual-launcher tests PASS on Linux; `bash -n` PASS.
macOS/exact-commit results must be recorded in PR #2 before handing over the helper.
This is a file-copy handoff, not approval of the held Queue-Details/runtime packages.
The original cabf37d macOS runtime FAILs and #3 remain open. No attempt was made
to repair them or rerun them to green in this step. Product release remains blocked.

**Actual notification source, native proof, SYNC-001: NOT RUN/BLOCKED.**
