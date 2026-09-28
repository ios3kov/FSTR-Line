# Development Status

## Current branch

`feat/phase0-cep-poc`

## Baseline

Before implementation the repository contained documentation only. No executable panel, Core, build, tests, or AE integration existed.

## Research completed for Phase 0A

- Adobe CEP Samples: official After Effects panel structure and CEP host bridge pattern.
- After Effects Scripting Guide: `Layer.id`, timing properties, `CompItem.frameDuration`, `displayStartFrame`.
- Adobe CEP → UXP migration guide: keep Core independent from CEP.
- ExtendScript JSON behavior: JSON is not guaranteed in the host runtime and must be bundled by the extension before host↔panel JSON transport is used.

## Implemented — Phase 0A

- platform-independent Timeline Core;
- frame/seconds conversion helpers;
- Z-order-safe packing engine;
- packing invariant validator;
- regression tests for sequential clips, overlaps, nested ranges, zero-gap, negative time and 23.976 frame conversion;
- dependency-free CI using Node's built-in test runner.

## Packing decision

A naive "first free track" algorithm is rejected.

Reason: an overlap chain can place a lower AE layer on a visually higher track even when both layers overlap in time.

Current rule:

> For every overlapping pair, the lower AE layer must have a strictly larger visual track index.

This preserves After Effects compositing order at all overlap times.

## Validation status

Automated validation is available for the platform-independent Core.

Real After Effects profiling and host integration testing are not yet applicable because the CEP host adapter has not been committed in this stage.

## Next

Phase 0B:

1. dockable CEP manifest;
2. ExtendScript host adapter;
3. self-contained JSON transport;
4. read-only active-composition snapshot;
5. panel rendering using the tested packing Core;
6. select / move / trim / undo commands.
