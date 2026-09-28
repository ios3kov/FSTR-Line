# AE 25.6 read/refresh smoke test

- Test Run ID: `FSTR-CEP-READ-REFRESH-2026-09-28-01`.
- Target: AE `25.6.0.101`, macOS `26.6.2`, Apple M1 Pro, 16 GB RAM; bundled CEPHtmlEngine `12.0.1.2`.
- Installed artifact: `fstr-cep-aaa6da96ab91`, clean source `aaa6da96ab91d1a0509fdd9a158fc656fa450223`.
- Installation and payload hashes: [installation record](CEP-INSTALL-AE25-2026-09-28.md).
- Evidence: user-provided screenshot and subsequent confirmation in development conversation `ses_f17c04bacffdlASbDnoYNDmoaL`. Screenshot is retained in the conversation, not copied into this repository.
- Scope: user-observed smoke test, not an automated runtime test.

| Check | Expected / observed | Status |
| --- | --- | --- |
| Panel opens | Screenshot shows FSTR Line floating panel inside AE | PASS |
| Active composition read | Native Timeline shows two layers; panel shows `Comp 1: 2 layers, 2 tracks`, IDs `16` and `15` | PASS |
| Refresh after context/layer changes | User confirmed requested test: new test composition with one text layer shows `1 layers, 1 tracks`; adding a second and refreshing shows `2 layers, 2 tracks` | PASS |
| Sequential-layer packing | Requires controlled non-overlapping ranges | NOT RUN |
| Docking, save/reopen, restart persistence | No explicit test confirmation | NOT RUN |
| Full snapshot field accuracy and compositing invariance | Screenshot/count confirmation insufficient | NOT RUN |
| Loaded Build ID | Installed identity known; runtime identity not exposed by this panel | NOT RUN |
| Editing and Undo/Redo | Read/refresh-only UI | NOT RUN |

Opening and basic read/refresh are confirmed in this environment. The full integration gate remains open. No production-readiness or broader AE-version compatibility claim follows from this smoke test.
