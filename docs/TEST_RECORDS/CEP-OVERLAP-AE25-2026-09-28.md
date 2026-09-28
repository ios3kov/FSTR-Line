# AE 25.6 overlap refresh smoke test

- Test Run ID: `FSTR-CEP-OVERLAP-2026-09-28-01`.
- Environment: AE `25.6.0.101`, macOS `26.6.2`, Apple M1 Pro; bundled CEPHtmlEngine `12.0.1.2`.
- Installed artifact: `fstr-cep-aaa6da96ab91`, source `aaa6da96ab91d1a0509fdd9a158fc656fa450223`.
- Identity evidence: [installation record](CEP-INSTALL-AE25-2026-09-28.md); loaded runtime Build ID remains independently unverified.
- Initial state: two sequential layers on one packed track, as recorded in [packing smoke test](CEP-PACKING-AE25-2026-09-28.md).
- Procedure: user was asked to move the second layer left to introduce a temporal overlap, then click Refresh.
- Expected result: `2 layers, 2 tracks`.
- Actual result: user confirmed “всё так” in conversation `ses_f17c04bacffdlASbDnoYNDmoaL`.
- Status: **PASS**, user-reported manual smoke test.

This confirms the reported one-track to two-track transition after a native timing edit and Refresh. It does not verify exact snapshot fields, compositing invariance, runtime identity, save/reopen, restart, or editing through the panel.
