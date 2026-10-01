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

Current reviewed HEAD: `35c2c5d77cd3cba0ac1bdacb6d9320f22182851e`; checkpoint ancestor: `6bef1e475ef944cdd471a84041d7d4035b732d8c`.

The helper was hardened without changing the product architecture (FSTR Line remains CEP + ExtendScript; this AEGP bundle is research-only):

- module pinning is deferred until exact host identity is accepted and immediately before private Insert; clean pre-hook failures delete local State and do not pin the module;
- a unique private JSONL trace records Build ID, sequence, wall time and bounded diagnostic events on the AEGP main-thread path only; the BEE callback itself still performs no file I/O or project read;
- a strict trace parser rejects wrong identity/schema/order, private activity in the disabled build, missing own-ID removal, retained forwarding at exit, fewer than two active observations and non-increasing generations;
- the build embeds `Contents/Resources/FSTRChainProbeBuild.json` before signing, tying the research bundle to source commit/Build ID while keeping `AEGP_load=NOT RUN`, `SYNC-001=NOT RUN` and `handoffApproved=false` until real runtime evidence exists.

During implementation the trace tests exposed and preserved two actual failures before fix: literal JSONL newline handling and an over-escaped observation-generation regex. The final regex behavior has an explicit regression test. These were evidence-tool defects, not AE runtime results.

Exact-head CI: Integration gate `36833726253` PASS; Read-only module input `36833726379` PASS. Notification research tools `36833726281` completed the new research unit regression successfully, then failed in the unrelated existing LLDB owned-fixture test: two attach runs passed and the third ended with fixture cleanup exit `-9` after detach. This remains Issue #3 and is neither retried-to-green nor treated as a new SYNC-001 blocker.

The no-LLDB parser currently proves evidence shape/order only. It does not prove that observations correspond to the intended native/script/Undo/Redo operations or their post-commit state. That correlation is part of the real-AE gate and must not be inferred from two increasing generations.

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
