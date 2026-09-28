# CEP installation for AE 25.6

- Test Run ID: `FSTR-CEP-INSTALL-2026-09-28-01`
- Scope: build and first user-local installation; runtime checks pending.
- Target: After Effects `25.6.0.101`, confirmed from installed app Info.plist and user screenshot.
- Bundled CEPHtmlEngine: `12.0.1.2`, confirmed from its Info.plist.
- Environment: macOS `26.6.2`, Apple M1 Pro, 16 GB RAM.
- Build ID: `fstr-cep-aaa6da96ab91`
- Source commit: `aaa6da96ab91d1a0509fdd9a158fc656fa450223`, clean.
- Installed directory: `~/Library/Application Support/Adobe/CEP/extensions/com.ios3kov.fstrline`.
- Build metadata: installed `build-manifest.json` contains all six payload SHA-256 values.
- Client bundle SHA-256: `f794c23c075eb054177e1e895a84d93d64fc6352598ca70d6aff07a9a526ca24`.
- Host SHA-256: `111d57b0552c335f9cb18dbaefa46606f8b8cb0f4063886adc68e0f2dab4a541`.

## Procedure and results

| Check | Result | Evidence |
| --- | --- | --- |
| Clean source tree | PASS | `git status --short` empty before build |
| TypeScript and regression | PASS | `npm run check`: 30 tests, 0 failures |
| CEP build and static host syntax | PASS | `npm run build:cep` exited successfully |
| First-install state | PASS | User CEP directory empty; no matching manifest found in system CEP directory |
| CEP debug preference | PASS | Existing `com.adobe.CSXS.12 PlayerDebugMode` equals `1`; no preference changed |
| Installed payload identity | PASS | All six SHA-256 values checked before and after copy against generated manifest |
| Panel opening, docking and snapshot read | NOT RUN | Awaiting opening the installed panel in AE |
| Restart, save/reopen and runtime identity | NOT RUN | Installation hashes do not establish loaded-code identity |

No application was terminated or project modified. Next step: save work, restart AE, open Window → Extensions → FSTR Line, and read an active test composition. This record confirms installation only, not AE compatibility. Earlier unavailable-host records remain historical.
