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

## Implemented — Phase 0C\n\n- deterministic package builder from an explicit source allowlist;\n- SHA-256 BUILD_MANIFEST.json for packaged files;\n- package integrity verifier;\n- mocked AE host execution tests for snapshot/select/move/trim/Undo;\n- mocked CEP adapter tests for argument validation and host-error propagation;\n- CI packaging and artifact upload;\n- clean per-user macOS/Windows development installer;\n- stale FSTR Line CEP cache/log cleanup only;\n- duplicate system-extension detection;\n- unsigned CSXS 11/12 development-mode setup;\n- final automated code/security audit fixes: package verification before install, stale per-user bundle cleanup, no-op Undo prevention, sync bridge-error recovery.\n\n## Implemented — Phase 0D

- real-After-Effects runtime smoke JSX;
- clean-project safety gate;
- real host.jsx execution inside AE;
- runtime snapshot/select/move/trim validation;
- rejected-trim non-mutation check;
- save/reopen Layer.id persistence check;
- automatic test-project close without saving;
- macOS runner that refuses a pre-existing AE session and retrieves the structured result without requiring file-write permission;\n- macOS startup retry + DoScriptFile fallback to DoScript/$.evalFile for AE automation robustness.

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

Next: run the automated macOS real-AE smoke gate on an installed After Effects build, then capture real profiling. Drag/trim gesture UX comes only after the host bridge is proven stable.
