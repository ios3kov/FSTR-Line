# Performance Baseline

## Policy

Optimization is measurement-driven.

No code is called faster because it "looks faster". Any optimization that adds complexity must be justified by before/after measurements.

## Core baseline

Run:

    npm run benchmark:core

The benchmark uses deterministic timelines with:

- 10 layers;
- 50 layers;
- 200 layers;
- 500 layers;
- 1000 layers.

For each size it measures:

- sequential clips;
- fully overlapping clips;
- deterministic mixed timing.

Each scenario records min, median, mean, p95 and max wall-clock time plus resulting track count.

CI uploads the JSON result as `FSTR-Line-Core-Performance`.

These Node measurements validate the platform-independent algorithm only. They are not a substitute for profiling in After Effects.

## Real After Effects timings

`npm run smoke:ae` now records ExtendScript microsecond timings for:

- snapshot;
- selection;
- frame move;
- Trim In;
- Trim Out;
- rejected invalid trim;
- temporary project save/reopen;
- post-reopen snapshot.

ExtendScript `$.hiresTimer` measures microseconds elapsed since its previous read.

## Still required before production performance claims

Inside real After Effects:

- snapshot scaling at 10 / 50 / 200 / 500 / 1000 layers;
- panel render/layout cost;
- idle CPU while panel is open;
- memory delta;
- RAM Preview comparison with panel closed/open;
- render comparison with panel closed/open;
- Multi-Frame Rendering behavior;
- repeated move/trim latency;
- large-project UI virtualization profiling.

No compatibility/performance configuration is marked supported until measured.
