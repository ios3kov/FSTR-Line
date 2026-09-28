# Development Status

## Current branch

`feat/phase0-cep-poc`

## Baseline

Before implementation the repository contained documentation only. No executable panel, Core, build, tests, or AE integration existed.

## Research completed

- Adobe CEP 11/12 compatibility matrix and official `CSInterface.js`.
- Adobe After Effects CEP sample structure.
- After Effects Scripting Guide: `Layer.id`, timing properties, `CompItem.frameDuration`, `displayStartFrame`.
- Adobe CEP → UXP migration guidance: keep Core independent from CEP.
- ExtendScript JSON behavior: JSON is not guaranteed in the host runtime, so the extension vendors its own ES3-compatible JSON implementation.

## Implemented — Phase 0A

- platform-independent Timeline Core;
- frame/seconds conversion helpers;
- Z-order-safe packing engine;
- packing invariant validator;
- regression tests for sequential clips, overlaps, nested ranges, zero-gap, negative time and 23.976 frame conversion;
- dependency-free CI using Node's built-in test runner.

## Implemented — Phase 0B

- dockable CEP panel manifest targeting AE 22+ with CSXS 11 minimum;
- official Adobe CEP 11 `CSInterface.js` bridge;
- self-contained ExtendScript JSON transport;
- read-only active-composition snapshot;
- native persistent `Layer.id` identity;
- compact visual track rendering using Timeline Core packing;
- AE layer selection from the panel;
- frame-step Move, Trim In and Trim Out;
- one native AE Undo group per edit;
- explicit host errors returned to the UI;
- no Node.js, filesystem or network permissions enabled.

## Packing invariant

A naive "first free track" algorithm is rejected.

> For every overlapping pair, the lower AE layer must have a strictly larger visual track index.

This preserves After Effects compositing order at all overlap times.

## Automated validation

- Core syntax check;
- Core unit tests;
- CEP browser-side syntax checks;
- ExtendScript syntax parse check after removing the preprocessor include line;
- manifest security/contract checks;
- Undo-group contract checks;
- self-contained dependency checks.

## Implemented — Phase 0C

- deterministic package builder from an explicit source allowlist;
- SHA-256 BUILD_MANIFEST.json for packaged files;
- package integrity verifier;
- mocked AE host execution tests for snapshot/select/move/trim/Undo;
- mocked CEP adapter tests for argument validation and host-error propagation;
- CI packaging and artifact upload;
- clean per-user macOS/Windows development installer;
- stale FSTR Line CEP cache/log cleanup only;
- duplicate system-extension detection;
- unsigned CSXS 11/12 development-mode setup;
- final automated code/security audit fixes: package verification before install, stale per-user bundle cleanup, no-op Undo prevention, sync bridge-error recovery.

## Implemented — Phase 0D

- real-After-Effects runtime smoke JSX;
- clean-project safety gate;
- real host.jsx execution inside AE;
- runtime snapshot/select/move/trim validation;
- rejected-trim non-mutation check;
- save/reopen Layer.id persistence check;
- automatic test-project close without saving;
- macOS runner that refuses a pre-existing AE session and retrieves the structured result without requiring file-write permission;
- macOS startup retry + DoScriptFile fallback to DoScript/$.evalFile for AE automation robustness.

## Implemented — Phase 0E

- deterministic Core performance baseline for 10/50/200/500/1000 layers;
- sequential, full-overlap and mixed timing scenarios;
- CI performance JSON artifact;
- real-AE smoke timing instrumentation using ExtendScript high-resolution timing;
- measurement policy documented before optimization.

## Implemented — Phase 0F

- real-AE host stress harness for 10/50/200/500/1000 layers;
- snapshot + serialization timing at each scale;
- bottom-layer worst-case selection lookup timing;
- bottom-layer move + refresh timing;
- recorded Core baseline shows no current need for a more complex packing algorithm.

## Implemented — Phase 0G

- full production timing matrix tests: 23.976 / 24 / 25 / 29.97 / 30 / 50 / 59.94 / 60 fps;
- negative display-start and large positive/negative frame roundtrips;
- frame-safe host move/trim tests across the same FPS matrix;
- identical In/Out stacking regression;
- very long frame-range regression.

## Implemented — Phase 0I

- Windows real-AE launcher via documented AfterFX.exe -r execution;
- process exit-code contract using app.exitCode;
- automatic Windows exit after external smoke via app.exitAfterLaunchAndEval;
- AE memory-in-use baseline around 10–1000 layer stress;
- one-command clean install + runtime smoke through npm run validate:ae.

## Implemented — Phase 0J

- generated Build Identity embedded during packaging;
- Build ID includes version, exact Git commit and clean/dirty source state;
- browser and After Effects host receive metadata from the same package run;
- Diagnostics compares browser/host Build ID and commit;
- dirty packages are rejected by clean verification;
- CI checks exact head commit and verifies source tree cleanliness before/after packaging.

## Implemented — Phase 0K

Automated pre-AE hardening added after Build Identity:

- safe installer boundaries: no automatic PlayerDebugMode/security mutation and no termination of a pre-existing AE process;
- unknown duplicate CEP bundles cause BLOCKED instead of deletion;
- rollback-capable replacement of the identified FSTR Line per-user target;
- runtime smoke is bound to the installed CEP Build ID and exact installed file hashes;
- unique Test Run ID and isolated runtime workspace;
- structured PASS / FAIL / BLOCKED runtime test records;
- exact installed payload file-set validation, including stale-file and path-traversal rejection;
- Undo exception/recovery and repeated-execution coverage;
- panel lifecycle/double-action/Build Identity mismatch coverage;
- automated static code/security audit;
- GitHub Actions pinned to immutable commit SHAs;
- third-party source/license notices recorded.

## Current verification state

### PASS — automated scope

The current branch has automated coverage for:

- syntax/static checks;
- Timeline Core packing and timing matrix;
- deterministic randomized packing invariants;
- host bridge snapshot/select/move/trim behavior in the mock host;
- Undo Group closure on exceptions and repeated operations;
- CEP adapter argument/error handling;
- panel no-comp lifecycle and accidental double-action suppression;
- Build Identity generation and browser/host identity contract;
- clean package and SHA-256 verification;
- exact installed-payload verifier behavior;
- safe installer contract;
- real-AE runner contract for macOS and Windows;
- unique Test Run ID and structured Evidence record contract;
- static security/code audit;
- Core performance sanity benchmark through 1000 layers.

The exact current Build ID, artifact digest and Level-1 run are recorded outside this source document in CI/PR Evidence, because changing this document itself creates a new Git commit and therefore a new Build ID.

### BLOCKED — requires an actual After Effects runtime

The following required Phase 0 runtime checks are not claimed as PASS because the current tool environment has no accessible installed/licensed After Effects instance:

- actual clean CEP installation/load in After Effects;
- runtime Build ID read from the code actually loaded by AE;
- dock/floating panel behavior;
- native Timeline ↔ FSTR snapshot equality;
- real select / Move / Trim In / Trim Out;
- real Undo / Redo;
- save/reopen Layer.id persistence;
- close/reopen/reload/restart lifecycle;
- panel resize / small-size / HiDPI / Retina behavior;
- cold/warm runtime behavior;
- real host-call latency and UI responsiveness;
- real memory/idle-load behavior;
- 10 / 50 / 200 / 500 / 1000 layer stress profiling inside AE;
- macOS and Windows compatibility rows.

Unblock condition: execute the identified clean CEP artifact with the automated validation runner on a machine that has the target After Effects version and the required CEP loading permission. If unsigned CEP development is disabled, explicit permission or a signed package is required; the installer will not alter the security setting automatically.

### N/A — Phase 0 CEP panel

These render/effect checks do not apply to the current CEP panel because it does not implement an After Effects pixel/render effect or render callback:

- GPU render path;
- MFR;
- Smart Render;
- ROI;
- 8/16/32-bpc pixel processing;
- Linear/OCIO/HDR pixel correctness;
- CPU/GPU pixel parity;
- aerender render-output correctness.

UXP sandbox checks are also N/A for Phase 0 because the current implementation is CEP. They become required if/when a real AE UXP adapter is introduced.

Signing/public-distribution validation is outside the current internal Phase 0 PoC and remains required before a distributable release.

## Evidence policy

- CI/mock Evidence proves only its stated automated scope.
- Static audit/hash Evidence proves security/identity properties, not real AE behavior.
- A successful runtime smoke on one configuration will verify only that recorded configuration and scope, not all supported platforms.
- Historical FAIL runs are retained as Evidence of issues found and corrected; they are not rewritten as PASS.

## Next gate

Run the automated installed-artifact validation in real After Effects, persist its Test Run record, then perform the remaining runtime/UI/Undo/performance checks required by the Phase 0 gate. Drag/trim gesture UX remains after host-bridge runtime validation.
