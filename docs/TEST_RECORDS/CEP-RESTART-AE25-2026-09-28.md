# AE 25.6 save/reopen and restart smoke test

- Test Run ID: `FSTR-CEP-RESTART-2026-09-28-01`.
- Environment: AE `25.6.0.101`, macOS `26.6.2`, Apple M1 Pro; bundled CEPHtmlEngine `12.0.1.2`.
- Installed artifact: `fstr-cep-aaa6da96ab91`, source `aaa6da96ab91d1a0509fdd9a158fc656fa450223`.
- Artifact hashes: [installation record](CEP-INSTALL-AE25-2026-09-28.md).
- Initial state: test composition with two overlapping layers, two packed tracks, as recorded in [overlap smoke test](CEP-OVERLAP-AE25-2026-09-28.md).
- Procedure requested: save the test project, close and reopen AE and the project, open the test composition, click Refresh.
- Expected: two layers, two tracks and unchanged layer IDs.
- Actual: user confirmed “всё так” in conversation `ses_f17c04bacffdlASbDnoYNDmoaL` after receiving these steps.
- Status: **PASS**, user-reported manual smoke test of save/reopen and restart followed by read/refresh.

This confirms the reported counts and ID persistence in this scenario. No new screenshot, raw snapshot or runtime Build ID was collected. It does not establish exact timing/switch accuracy, automatic workspace restoration, full compositing invariance, editing or Undo/Redo correctness. Earlier NOT RUN records describe their respective earlier test runs and remain historical.
