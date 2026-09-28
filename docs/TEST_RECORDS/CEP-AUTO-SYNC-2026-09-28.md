# Opt-in active composition monitoring

- Run: `FSTR-CEP-AUTO-SYNC-2026-09-28-01`.
- Baseline: user-confirmed automatic composition discovery; continuous native edit synchronization not previously implemented.
- Build: `fstr-cep-b1a7f7995f53`, clean source `b1a7f7995f537a6f3d028bc16ca6d5ec2de3da83`.
- Client SHA-256: `f85af385dfd7303bd3d57e72270ce2b667e5783d9c132da7407d22e5e8655d64`.
- Host SHA-256: `57f0233ca74ad4cf53afb88e870fa902a9cbcadface7f25679bba89ac603bb9f`.
- Target: established AE 25.6/M1 Pro test environment.

## Checks

- PASS: 45 local tests, TypeScript build, static host syntax, clean CEP build.
- PASS: new scheduler coverage for repeated reads, disabling, suspension during pending read and stopping on error.
- PASS: installed six payload hashes verified; full manifest in installed `build-manifest.json`.
- NOT RUN: native timing edits/add/delete/selection → automatic panel update in AE.
- NOT RUN: CEP visibility behavior, long-running load, 50/200/500-layer profiling, runtime identity for this candidate.

Opt-in design limits continuous activity until measured. Only active composition is read, at 2-second intervals after completion; no writes, no 100–200 ms project polling. Full snapshot cost remains O(layer count) and projection rebuild is not yet incremental. No performance guarantee is claimed.

Backup: `~/Library/Application Support/FSTR-Line/backups/20260928-185024`; restore this payload to extension directory and restart AE for rollback. No application stopped or project edited by installation.

Acceptance: restart AE, verify MATCH Build ID, enable Auto Sync (2s), edit overlap/add/remove a layer in native Timeline and wait without Refresh or returning focus to FSTR. Check expected track/count changes. Disable Auto Sync and verify periodic bridge calls stop. Runtime evidence is required before declaring this scenario working.
