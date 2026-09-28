# AE 25.6 sequential packing and docking smoke test

- Test Run ID: `FSTR-CEP-PACKING-2026-09-28-01`.
- Environment: AE `25.6.0.101`, macOS `26.6.2`, Apple M1 Pro; bundled CEPHtmlEngine `12.0.1.2`.
- Installed artifact: `fstr-cep-aaa6da96ab91`, source `aaa6da96ab91d1a0509fdd9a158fc656fa450223`.
- Payload identity: [installation record](CEP-INSTALL-AE25-2026-09-28.md). Runtime Build ID is still not independently confirmed.
- Evidence: subsequent user screenshot in conversation `ses_f17c04bacffdlASbDnoYNDmoaL`, following the requested sequential-layer test. Screenshot retained in conversation.

| Check | Expected / observed | Status |
| --- | --- | --- |
| Sequential layers share a track | Native Timeline shows two adjacent layer bars in Comp 2; panel shows `Comp 2: 2 layers, 1 tracks` and `V1: 31 · 29` | PASS |
| Panel docks in AE workspace | FSTR Line is visibly docked between Composition viewer and Timeline | PASS |
| Exact frame boundary values | Screenshot shows adjacency but does not expose numeric in/out values | NOT RUN |
| Refresh after introducing overlap | Requires subsequent test | NOT RUN |
| Restart/save/reopen persistence | Requires explicit confirmation | NOT RUN |

Scope: visible packing result and docking in this one configuration. This does not establish complete snapshot accuracy, compositing invariance, editing/Undo behavior or full lifecycle compatibility.
