# Bounded empty-response recovery

- Test Run ID: `FSTR-CEP-RECOVERY-2026-09-28-01`.
- Baseline: initial empty snapshot/identity responses on AE 25.6, recovered by manual Refresh; see `CEP-DIAGNOSTICS-RUNTIME-2026-09-28.md`.
- Root cause: unknown. No new live AE reproduction captured during this implementation.
- Scope: bounded read-only recovery and payload-free diagnostics; no command retries.
- Build ID: `fstr-cep-4892294f436c`.
- Clean source: `4892294f436c672a16fb5a120b5445fce9005699`.
- Client SHA-256: `96a98d552b2f0df8b3ca0670adf85c627137982982946b06ff7a1421d8ad1a2a`.
- Host SHA-256: `be93f15ded026692826dd4a761dbec886ffd22d244ea3cc01edf988d3e0e8930`.
- All payload hashes: installed/generated `build-manifest.json`.

| Check | Status | Evidence |
| --- | --- | --- |
| TypeScript / regression | PASS | 39 tests, 0 failures |
| Empty read recovery and queue ordering | PASS | Simulated empty reply then valid snapshot; subsequent read waits |
| Exhaustion / manual retry | PASS | Exactly three failed attempts, subsequent requested read succeeds |
| Commands, errors and timeouts not replayed | PASS | Dedicated tests; late callback ignored |
| Diagnostics observer isolation | PASS | Throwing observer cannot fail successful read |
| Clean packaging / static host syntax | PASS | `npm run build:cep` after source commit |
| Installation identity | PASS | Six hashes verified for existing baseline, new package and installed replacement |
| AE startup recovery | NOT RUN | New artifact must load in AE; unit tests are not runtime evidence |

Previous installation backed up to `~/Library/Application Support/FSTR-Line/backups/20260928-182153`. AE was not terminated, no project modified. Restore that directory to the extension path and restart AE to roll back.

Next: save work, restart AE, open an active composition and panel without clicking Refresh. Capture Diagnostics with loaded Build IDs and bridge attempt log. A successful first read alone does not reproduce or prove recovery from the baseline failure. Root-cause investigation remains open; bounded retries are documented as a workaround in `cep/README.md`.
