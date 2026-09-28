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


## Recorded Core baseline — commit 6863b51

GitHub Actions / Node 22 baseline, p95:

| Layers | Sequential | Full overlap | Mixed |
|---:|---:|---:|---:|
| 10 | 0.005 ms | 0.007 ms | 0.008 ms |
| 50 | 0.106 ms | 0.109 ms | 0.007 ms |
| 200 | 0.059 ms | 0.083 ms | 0.037 ms |
| 500 | 0.218 ms | 0.383 ms | 0.308 ms |
| 1000 | 0.902 ms | 1.216 ms | 1.395 ms |

Decision: do not complicate the current packing algorithm yet. The current Core cost is already low at the v1 stress target; actual After Effects host/UI cost is the next measurement target.

## AE host scaling captured by the runtime smoke

The real-AE smoke now creates isolated 10 / 50 / 200 / 500 / 1000-layer compositions and records:

- full snapshot + JSON serialization time;
- worst-case bottom-layer selection lookup;
- worst-case bottom-layer move lookup + edit + snapshot.

The stress project is unsaved and closed without saving.
