# Bounded composition discovery

- Run: `FSTR-CEP-DISCOVERY-2026-09-28-01`.
- Baseline runtime evidence: user screenshot of `fstr-cep-4892294f436c` shows snapshot attempts empty (11 ms), empty (3 ms), response (7 ms), then NO_ACTIVE_COMP. Diagnostics MATCH, AE 25.6x101. User subsequently confirmed Refresh displayed layers. Evidence retained in conversation `ses_f17c04bacffdlASbDnoYNDmoaL`.
- Baseline transport recovery: PASS; automatic composition acquisition: FAIL in that run. Cause/timing of AE activeItem availability and empty replies remains unproven.
- New clean source: `3c6a6297b9b4f1b74b9c6b876b53335bc2d2207d`.
- Build ID: `fstr-cep-3c6a6297b9b4`.
- Client SHA-256: `1b59cd7e52cdd943d320b3213dec7fa1ed5a98028f0a1a313ec5dbbf8dcfb56e`.
- Host SHA-256: `f285b054ede361d9e52bd3d2019ec5dee13243195ef0033b1d216601aafbc7ee`.

## Checks

- PASS: TypeScript and 42 local tests, including bounded discovery, disposal, hidden-panel suppression, concurrent request suppression, success stopping discovery, and typed no-composition clearing/recovery.
- PASS: clean CEP packaging and static host syntax after source commit.
- PASS: installed payload hashes checked before replacement and all six new hashes checked after copy.
- NOT RUN: new build startup behavior, CEP focus/visibility event delivery, close/reopen and automatic composition recovery in AE.
- NOT RUN: exact snapshot field accuracy and full integration gate.

Previous installation backup: `~/Library/Application Support/FSTR-Line/backups/20260928-183559`. Restore to the extension directory and restart AE for rollback. No project edits, process termination or preference changes.

## Runtime acceptance

Restart AE with saved test project, open test composition within discovery window, do not press Refresh. Expect MATCH for new Build ID and layers appearing automatically. If no composition exists, expect a neutral prompt; after 15 attempts polling stops. Test returning focus to the panel after opening/changing composition. Capture bridge log and resulting snapshot. This remains a bounded discovery mechanism, not ongoing native Timeline synchronization.
