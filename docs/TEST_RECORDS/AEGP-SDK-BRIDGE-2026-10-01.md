# AEGP SDK bridge implementation — 2026-10-01

Run: `AEGP-SDK-BRIDGE-20261001-01`. Baseline: `adf3ec85e4bf11a7f63bc157b61a9453eda587e3`.
Branch `integration/host-safety-notifications`, PR #2 Draft/unmerged. Phase 0, 0/5 accepted.
Main rules reread; blob `701a8c1ae3acb4dbfe1d7eda94acbf8095b88608` unchanged.
Scope: the minimal native source -> AEGP idle -> current active-layer observation.
Not a general collector/LLDB repair, product integration, install or runtime acceptance.

## Inputs and SDK contracts

The user supplied the matching SDK. Its `.tar.zstd.zip` file is Zstandard data,
not a ZIP container: SHA-256 `e02fa2b488c3cceb238866b648eb9a2526d308a260744367915a2f173663c36c`.
The separately supplied `.tar.zstd` is already a TAR. Format was inspected before
extracting with the environment's zstd/tar. The supplied xattr script and macOS
zstd executable were not executed. No SDK or Adobe-library bytes are committed/uploaded to CI.

`Examples/Headers/AE_GeneralPlug.h` SHA-256:
`30d12ec3eb5af1a902c7414053b1be1da0204b226e0b1cdc71272be1e137000c`.
Actual declarations used: `AEGP_PluginInitFuncPrototype`, RegisterSuite5 (version 6),
CommandSuite1, UtilitySuite6 (version 13), LayerSuite9 (version 15), and command,
menu, idle and death hook signatures. Compile-time type assertions verify those
hook/entry types, rather than inventing header layouts or suite version numbers.

The UtilitySuite6 comment at lines 3008-3013 documents asynchronous wake and
requires caching the function pointer on the main thread. LayerSuite9 explicitly
returns an active layer only for exactly one selected layer. A null active layer
is recorded as absent, not interpreted as complete composition coverage.
The SDK samples' PiPL resource and bundle metadata were inspected to prepare the
build recipe. No sample/SDK implementation is redistributed here.

## Implementation and acceptance boundaries

The dispatcher coalesces event generations without a timer or revision polling.
A source callback always forwards the original message and preserves its result
and exceptions. Only successful selected research events request a fresh read.
An error remains in the observer's error counters; this is not a guarantee of
synchronizing partial failed host operations. Neither a zero return nor a snapshot
is a transaction commit acknowledgement. Repeated-edit behavior in real AE is still unknown.

An idle read uses public active-layer/ID/offset/in-point/duration APIs and retains
only numeric values. In-flight/nested reads are deferred; a new event during the
read makes the sample superseded. A failed read keeps pending work but prevents
blind retries on every idle. Another real event permits a new attempt. Wake failure
is counted; pending is not discarded and a later real event may request wake again.
No-event, disabled and noninteractive cases do not read the project.

The macOS binding verifies exact main bundle ID/version and two existing image
handles using RTLD_NOLOAD/RTLD_FIRST. It compares file hashes, UUIDs, mapped headers
and complete text sections, then checks registration/removal export ownership.
It never loads missing Adobe modules. Successful handles, module and refcon remain
pinned; failure before registration cleans acquired image handles. No image enumeration
race is introduced. Primary Apple method references:
- https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man3/dlopen.3.html
- https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man3/dladdr.3.html

Exact identity is a precondition, not proof of a correct private ABI or safe host
lifecycle. In particular, local callback depth is not registry-wide quiescence.
Private registration is disabled in default builds, separately opt-in for isolated
research. Unknown insert/remove outcomes block retries; callback/refcon memory
is never freed under a possible remaining subscription. SDK death disables recording
and releases acquired suites but deliberately does not mutate a tearing-down BEE
registry. Native registration/removal concurrency remains an unaccepted runtime gate.

## Post-checkpoint hardening and evidence gate

Current reviewed HEAD: `21a2d0599d1bdbff6cc6d960a79bc9cf6e0de4d8`; checkpoint ancestor: `6bef1e475ef944cdd471a84041d7d4035b732d8c`.

The helper was hardened without changing the product architecture (FSTR Line remains CEP + ExtendScript; this AEGP bundle is research-only):

- module pinning is deferred until exact host identity is accepted and immediately before private Insert; clean pre-hook failures delete local State and do not pin the module;
- a unique private JSONL trace records Build ID, sequence, wall time and bounded diagnostic events on the AEGP main-thread path only; the BEE callback itself still performs no file I/O or project read;
- a strict trace parser rejects wrong identity/schema/order, private activity in the disabled build, missing own-ID removal, retained forwarding at exit, fewer than two active observations and non-increasing generations;
- the build embeds `Contents/Resources/FSTRChainProbeBuild.json` before signing, tying the research bundle to source commit/Build ID while keeping `AEGP_load=NOT RUN`, `SYNC-001=NOT RUN` and `handoffApproved=false` until real runtime evidence exists.

During implementation the trace tests exposed and preserved two actual failures before fix: literal JSONL newline handling and an over-escaped observation-generation regex. The final regex behavior has an explicit regression test. These were evidence-tool defects, not AE runtime results.

Exact-head CI: Integration gate `36833726253` PASS; Read-only module input `36833726379` PASS. Notification research tools `36833726281` completed the new research unit regression successfully, then failed in the unrelated existing LLDB owned-fixture test: two attach runs passed and the third ended with fixture cleanup exit `-9` after detach. This remains Issue #3 and is neither retried-to-green nor treated as a new SYNC-001 blocker.

The no-LLDB parser now supports an exact, Build-ID-bound expected-state plan. For that mode it requires the exact observation count/order and exact active-layer `id`, `offset`, `in` and `duration`, and rejects snapshot-read failures. This improves repeated-state/post-read evidence. It still does not prove action origin (native UI, script, Undo/Redo) without independent controlled real-AE ground truth.

## Checks defined and executed

Required for this increment: actual supplied SDK declaration compilation, execution
of the new AEGP/dispatcher sources against owned host suites, default-off and failure
controls, optimized/ASan/UBSan dispatch tests, macOS loader compilation/refusal,
source/build-script syntax and clean Git diff. A full real macOS SDK bundle build,
PiPL/signing/host load and repeated edits are separate mandatory gates before handoff.

Local environment: Linux x86_64; Clang 17.0.0; source subset (GitHub clone failed DNS).
The unchanged observer and chain ABI files match their original Git blob hashes.
Two unittest methods PASS, one macOS-only loader method NOT RUN locally. The actual SDK control executes eight fresh-process scenarios: normal repeated/coalesced events, noninteractive host, partial hook registration, wrong-host bind, unexpected callback thread, module-pin failure, death-hook registration failure and private-registration-disabled build. It also covers downstream errors,
exception identity, nested idle, failed-read backoff, wake errors, explicit own-ID
removal and late forwarding after deactivation. Actual C++ implementation is used;
the SDK suites, registry and OS binder around it are explicitly owned substitutes.

The SDK control selects the SDK's own Android preprocessor branch on Linux. This
is a declaration/C++ behavior check, NOT an Apple ABI check, Mac plugin build or
claim of Android support. No handwritten SDK declarations or fake Apple headers.
Independent portable dispatcher controls PASS in optimized and ASan/UBSan builds,
including superseded reads, no idle polling, stale-generation discard and overflow.
ASan leak detection is off for the deliberately process-resident refcon fixture;
ASan memory errors and UBSan remain fatal. No performance claim follows.

Python AST and whitespace checks PASS. The build script refuses Linux before
creating output. A native SDK bundle was NOT built locally. The recipe fixes the SDK header hash, records all SDK header inputs and final signed payload hashes, embeds the fail-closed research ownership receipt before signing, requires clean Git and does not install/launch AE or modify security preferences.
macOS exact-commit results are recorded in PR #2; previous successes are not reused.
The separate existing LLDB #3 FAIL is not repaired or waived by this work.

## Build-hardening follow-up — compiled PiPL verification

The macOS builder now treats the compiled PiPL itself as an acceptance input, not
only the source `.r` file. After `Rez -useDF`, it runs `DeRez` against the exact
generated `FSTRChainProbe.rsrc` with the supplied SDK type declarations and blocks
unless there is exactly one PiPL resource ID 16000 with `Kind { AEGP }`, name
`FSTR Chain Probe`, category `General Plugin`, and
`CodeMacARM64 { "EntryPointFunc" }`.

A pure regression test exercises the parser against valid output and rejects wrong
Kind, wrong name, wrong entry point and duplicate PiPL resources. This is build
hardening only: it does not claim that the bundle loaded in AE. Real Apple Silicon
Rez/DeRez execution remains part of the native build gate.

## Next real gate

Run the full recipe with the provided SDK on an authorized Apple Silicon build
machine, then validate PiPL, native entry/loader checks and disabled startup. No
licensed SDK is published to the public repository to make CI green. The hosted
macOS job can test the OS-only loader but does not have this conversation's private
SDK input; that absence is explicit, not a successful full build.

Only then perform the opted-in pass-through/register/repeated-edit/stop proof on a
disposable project without LLDB, preserving unrelated subscribers and host state.
Project/comp identity, post-commit timing, native/script/other-plugin origins,
selection/playhead coverage, callback interference/removal and performance remain
NOT RUN/BLOCKED. No plugin is handed to the user. SYNC-001 remains open.

## Exact-head follow-up — 21a2d05

Commit `21a2d0599d1bdbff6cc6d960a79bc9cf6e0de4d8` adds strict expected-state correlation to the no-LLDB trace gate and regression coverage for state mismatch, extra observations, malformed observations and snapshot-read failure. Integration gate `36834338257` PASS; Read-only module input `36834338195` PASS. Notification research tools `36834338125` passed the new research unit regression, then failed only in the existing LLDB owned-fixture path with post-detach fixture exit `-9`. Issue #3 remains open; no retry-to-green or LLDB fix is part of this stage.

Real Apple Silicon SDK bundle build, AE load, disabled-start runtime, controlled repeated changes, script-origin, Undo/Redo and safe Stop remain NOT RUN in this environment. SYNC-001 remains open and Phase 0 remains 0/5 accepted.

## Exact-head follow-up — 0ff7476

Commit `0ff7476a6b95edaea2693f8740ddc6874c8b70df` closes an evidence-quality gap in the no-LLDB script-origin gate. Previously the runner could accept four new stable observations after edit/edit/Undo/Redo without proving that those observations contained the actual post-action states. The runner now reads the active test layer through the public ExtendScript DOM after every controlled action, records `id/startTime/inPoint/duration` as an independent ground-truth sequence, and requires the AEGP trace to match that sequence exactly in count/order and rational time value. Equivalent rational scales are accepted; different values are rejected. Regression tests cover public-state parsing, malformed state, rational-scale equivalence and existing mismatch/error cases.

Exact-commit CI: Integration gate `36843261930` PASS; Notification research tools `36843262065` PASS; Read-only module input `36843262009` PASS. No real AE process was launched by these CI checks. Real Apple Silicon SDK bundle build and the disabled-start/script-origin AE runtime gates remain NOT RUN here. SYNC-001 remains open; Phase 0 remains 0/5 accepted.

## Runtime-runner safety hardening — 2026-10-01

Code review found and fixed fail-open cleanup risks before the real AE gate. The disabled-start runner now proves the launched AE project is empty and unsaved before issuing Quit; an auto-restored/non-empty or otherwise unprovable startup project is BLOCKED and is never closed automatically. Both disabled-start and script-origin runners refuse to remove the research bundle while AE is still running, and also refuse removal when process state cannot be established. Script-origin additionally marks project ownership unknown before the first mutating create call, so a partial create failure cannot be mistaken for an empty project. Private subscription recovery is stateful: a known-active probe gets one bounded Stop attempt; once the Stop/Remove outcome becomes unknown, the runner will not toggle again, close the project, quit AE, or remove the loaded bundle. Trace cleanup follows the same process-state rule. Regression tests cover unproven startup state, unknown process cleanup, partial project creation and failure after active registration. This is safety hardening only; real AE 25.6.0.101 runtime acceptance remains NOT RUN.

## Callback attribution ordering hardening — 2026-10-01

The script-origin runner now waits for a new AEGP observation immediately after each edit/Undo/Redo and only then performs the public ExtendScript layer-state read used as ground truth. This removes the control read itself as a possible source of the callback credited to that phase. The strict final parser still requires the exact four-state sequence, so a read-triggered extra stable observation fails closed instead of being accepted. Added regression coverage asserts the call order `count -> action -> wait -> read`. This is runner/evidence hardening only; real AE 25.6.0.101 runtime acceptance remains NOT RUN.

## Exact-head follow-up — 0436701

Commit `0436701ae6f83c600ccb2abaf8a1edb65165c049` makes the script-origin Undo/Redo sequence explicit and reproducible. Each controlled timing edit is wrapped in its own `app.beginUndoGroup("FSTR Chain Probe Script Edit")` / `app.endUndoGroup()` pair with `try/finally`, so the two edits are deliberately separate undoable actions before the runner executes Undo then Redo. A regression test verifies one balanced group per edit and that the mutation occurs inside the group.

Exact-commit CI: Integration gate `36869059679` PASS; Notification research tools `36869059643` PASS; Read-only module input `36869059698` PASS. The macOS research workflow also passed its legacy LLDB steps on this run, but intermittent Issue #3 remains open and is not reclassified by a single successful run.

This is evidence/run-control hardening only. No real AE 25.6.0.101 process was launched by CI; the Apple Silicon SDK bundle build and disabled-start/script-origin runtime gates remain NOT RUN here. SYNC-001 remains open; Phase 0 remains 0/5 accepted.

## Exact-head follow-up — 5129fcb

The runtime runner no longer resolves the Undo/Redo menu commands after creating named undo groups. Adobe's scripting contract requires `findMenuCommandId(command)` to match the text exactly as shown in the UI, while `beginUndoGroup(undoString)` changes the Edit-menu Undo text. To avoid that dynamic-label dependency, the runner now resolves `Undo` and `Redo` IDs before any project mutation, requires two distinct positive IDs, records them in evidence, and later calls `app.executeCommand(id)` directly for the two phases.

Commit `865a99810c676a7fff767af5f34e818fecdd39a6` initially added this behavior and correctly exposed a test-isolation defect: two existing failure-path unit tests reached real `osascript` on the macOS runner instead of mocking the new preflight. That commit's Notification Research unit step failed and is preserved as FAIL evidence. Commit `5129fcb1b8dce99e7c3b21ae99ad8e5e9c7a745a` fixes those test mocks without weakening the new preflight.

Exact `5129fcb` evidence: Research unit regression PASS; Integration gate `36870075957` PASS; Read-only module input `36870075731` PASS. Notification research tools `36870075728` reaches the legacy LLDB parent step and then fails in the already-open Issue #3 class; the new unit regression is green and no retry-to-green was used.

This remains runner/evidence hardening only. Full native Apple Silicon SDK bundle build in the user's AE environment, disabled-start load proof and script-origin Undo/Redo runtime proof are still NOT RUN here. SYNC-001 remains open; Phase 0 remains 0/5 accepted.
