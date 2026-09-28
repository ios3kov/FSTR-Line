# Phase 0 — Pre-After-Effects Gate

This record defines what can be proven before a real After Effects runtime is available.

Statuses follow DEVELOPMENT_RULES.md:

- PASS — executed and acceptance criteria met.
- FAIL — executed and criteria failed.
- BLOCKED — required, but current environment cannot execute it.
- NOT RUN — available but not executed.
- N/A — not applicable, with reason.

## Automated checks

| Check | Status | Evidence / scope |
|---|---|---|
| Exact Git HEAD checkout | PASS | CI checks out the PR/push head SHA, not a synthetic merge commit |
| Clean source state before build | PASS | CI git-status gate |
| JS/JSX syntax | PASS | Node syntax checks + JSX parser checks |
| Unit/integration mocks | PASS | Core, host, adapter, panel, package and runtime-runner contracts |
| Static code/security audit | PASS | artifacts/phase0-static-audit.json |
| Core performance sanity | PASS | deterministic benchmark through 1000 layers |
| Build Identity generation | PASS | generated build-info for browser + ExtendScript host |
| Dirty-build rejection | PASS | package verifier |
| Production file SHA-256 manifest | PASS | BUILD_MANIFEST.json |
| Exact installed payload verifier logic | PASS | rejects missing/extra/tampered/traversal/dirty payload fixtures |
| Safe installer contract | PASS | does not mutate PlayerDebugMode, kill existing AE, or delete unknown duplicate bundles |
| Runtime Test Run identity contract | PASS | unique Test Run ID; stale/mismatched report is rejected |
| Runtime Evidence record contract | PASS | PASS/FAIL/BLOCKED JSON record schema |
| Undo exception/recovery mocks | PASS | Undo Group closes via finally; bridge reusable after failure |
| Repeated execution mocks | PASS | repeated host operations do not leave open mock Undo transactions |
| Panel double-action guard | PASS | busy state suppresses second host call |
| Third-party source integrity | PASS | vendored CSInterface/json2 Git blob identities checked by static audit |

## Required real-AE checks

| Check | Status | Blocker / unlock condition |
|---|---|---|
| Clean first installation | BLOCKED | requires machine with target After Effects/CEP runtime |
| Runtime Build ID from loaded host code | BLOCKED | requires actual AE script/CEP load |
| Dock/floating panel load | BLOCKED | requires AE UI |
| Native Timeline snapshot parity | BLOCKED | requires AE composition |
| Real Move / Trim | BLOCKED | requires AE host operations |
| Undo / Redo | BLOCKED | requires native AE undo stack |
| Save/reopen persistent Layer.id | BLOCKED | requires real .aep lifecycle |
| Reload / close / reopen / restart | BLOCKED | requires AE lifecycle |
| Resize / minimum size / HiDPI | BLOCKED | requires AE/CEF UI |
| Cold/warm cache behavior | BLOCKED | requires controlled AE runtime |
| Host-call/UI latency | BLOCKED | requires real AE |
| Memory / idle load | BLOCKED | requires real AE |
| 10–1000 layer stress in host | BLOCKED | requires real AE |
| macOS compatibility row | BLOCKED | requires target macOS+AE configuration |
| Windows compatibility row | BLOCKED | requires target Windows+AE configuration |

## N/A for the current CEP panel

| Check | Status | Reason |
|---|---|---|
| GPU effect rendering | N/A | no pixel/render effect |
| MFR / Smart Render / ROI | N/A | no render callback |
| 8/16/32-bpc pixel correctness | N/A | panel does not process pixel buffers |
| Linear / OCIO / HDR render correctness | N/A | panel does not render image data |
| CPU/GPU pixel parity | N/A | no CPU/GPU effect implementations |
| aerender output parity | N/A | no render-path component |
| UXP sandbox/permissions | N/A | Phase 0 runtime is CEP |
| Helper-process lifecycle | N/A | no helper process exists |
| Settings migration | N/A | Phase 0 stores no persistent settings schema |
| File-dialog cancellation | N/A | Phase 0 exposes no file dialog |
| Signed public distribution | N/A for internal PoC | becomes required before distributable release |

## Gate decision

The automated pre-AE engineering work can be completed without user involvement.

Phase 0 is not ready to be called runtime-verified or ready for user acceptance until the BLOCKED real-AE checks required for the milestone have been executed against an identified clean artifact.
