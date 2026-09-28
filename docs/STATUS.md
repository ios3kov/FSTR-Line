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

## Latest Level 1 Evidence

Test Run ID: GitHub Actions `36424829531`

- Git commit: `98f94a87457db4d7d093b4a18d06596a2165d516`
- Build ID: `FSTR-Line@0.0.1+98f94a87457d.clean.cep`
- Git state: `clean`
- BUILD_MANIFEST SHA-256: `59f31d4b50e4a221a10b58aba60d14894301cb224a8dbdd7e88181edb7e62da0`
- GitHub CEP artifact digest: `sha256:8822be7b25024d2c52a0c103eaa3dfdf7bc52d0bab63f33d4369c07a4a4fb448`
- automated tests: `38 PASS / 0 FAIL`
- Core benchmark sanity: PASS
- clean package verification: PASS
- runtime Build Identity inside real After Effects: NOT RUN

Evidence scope: this confirms source/package identity and automated behavior covered by the test suite. It does not confirm real After Effects runtime behavior or platform compatibility.

## Not yet claimed

The CEP panel has not yet completed a clean real-After-Effects runtime run.

Therefore these are still unverified:

- actual dock/install behavior in the current AE build;
- native timeline ↔ snapshot equality on real projects;
- Undo behavior inside AE;
- save/reopen Layer.id persistence in the PoC;
- performance/profiling inside AE;
- compatibility matrix entries.

## Documentation audit

- README synchronized with executable PoC;
- Architecture synchronized with actual .js/.jsx module paths;
- planned-but-unimplemented modules explicitly separated from current code;
- no TODO/FIXME/HACK markers found in repository audit;
- stale literal newline escapes removed.

## Next gate

Next: execute the identified clean artifact through the automated real-AE validation gate on an available After Effects installation, verify runtime Build ID, then capture host/UI profiling. Drag/trim gesture UX comes only after the host bridge is proven stable.
