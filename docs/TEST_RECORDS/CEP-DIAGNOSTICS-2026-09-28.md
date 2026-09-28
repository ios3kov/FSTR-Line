# Loaded identity and snapshot diagnostics

- Test Run ID: `FSTR-CEP-DIAGNOSTICS-2026-09-28-01`.
- Baseline: user-reported read/refresh, packing, docking and restart smoke tests on AE 25.6, installed artifact `fstr-cep-aaa6da96ab91`.
- New clean artifact: `fstr-cep-92fd5e97d2fa`.
- Source: `92fd5e97d2fa6c21ebf0bad634c41ae5a5922635`, dirty false.
- Client SHA-256: `6445e197cb6f4f8025b787fb86aa700b6c71a003f0a658824abad53897198b18`.
- Host SHA-256: `0eccc98e931bb4040bb30aa7d5e557dda62eb970f01fab90972005e4975abd6e`.
- Full hashes: generated and installed `cep/build-manifest.json`.
- Environment: macOS development host, Node 24.13.1; AE target 25.6.0.101, CEPHtmlEngine 12.0.1.2.

## Results

| Check | Status | Evidence |
| --- | --- | --- |
| TypeScript + unit regression | PASS | `npm run check`: 33 tests, 0 failures |
| Clean CEP build + host syntax | PASS | `npm run build:cep` after source commit |
| Identity validation and stale/dirty mismatch | PASS | New diagnostics unit tests |
| Packaged diagnostics entrypoint | PASS (local only) | Node VM with stub app.version: returned build identity agrees with manifest; not an ExtendScript runtime test |
| Installed payload identity | PASS | All six payload hashes verified before and after installation |
| AE diagnostics UI / MATCH | NOT RUN | Requires reopening panel with new artifact |
| Exact timing/switch comparison | NOT RUN | Snapshot JSON available; independent native field comparison pending |
| New-artifact runtime regression | NOT RUN | Prior smoke evidence belongs to baseline artifact |

Previous installed payload verified before replacement and backed up to `~/Library/Application Support/FSTR-Line/backups/20260928-180612`. No AE process terminated, project modified or security preference changed. Rollback: restore the backed-up extension directory and restart AE.

## Next runtime check

Save work and restart AE. Open FSTR Line, Refresh, expand Diagnostics. Expect MATCH and both IDs `fstr-cep-92fd5e97d2fa`. Compare snapshot composition/layer IDs, indices, rational FPS, start/in/out frames and switches with native AE on a controlled fixture. Out frames are exclusive. Repeat no-composition/error recovery and read/refresh smoke tests. Full integration gate remains open until runtime evidence is collected.
