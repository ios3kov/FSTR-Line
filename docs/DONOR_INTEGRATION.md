# Donor integration inventory

Source: feat/phase0-cep-poc at 2cfb93fbb1ebc488ddf05471ab62b8d7606b68f5. Canonical base: main 15d995e5d27140690c1966f14b2aa0029989a072. Main and donor remain intact; this is selective integration, not a merge of incompatible products.

| Area | Decision | Evidence / remaining work |
|---|---|---|
| Core, normalized schema, semantic commands | Retain typed main implementation | src/core, src/host; donor JS Core is not imported |
| JSON compatibility | Copy donor json2 byte-for-byte | vendor/json2.js blob b43526d343e49b0f79c56bbc9a1e652a00834be7; embedded privately; notices included |
| Visual clips | Adapt approach to typed snapshot | src/cep/track-view.ts; proportional read-only spans, retained stale data; exact palette, controls and gestures still pending |
| CI / clean package | Adapt requirements, not incompatible package paths | .github/workflows/integration.yml, build-cep.mjs, verify-cep.mjs; exact allowlisted payload and commit identity |
| Host tests | Add canonical-host fault tests | actual JSX source and generated private JSON payload; model does not claim AE behavior |
| Donor host API and editing buttons | Do not copy directly | donor snapshot/commands differ and lack canonical guards; actual AE editing acceptance comes first |
| macOS/Windows installer and runtime runner | Deferred, preserve donor implementation | adapt identity/path/contract and safety, then verify; no silent import or deletion |
| Donor benchmark/stress/performance harness | Deferred | adapt canonical inputs and measure new implementation; donor performance figures cannot be attributed to this code |
| Direct notifications | Separate required research | research/ae-notifications; neither branch implements SYNC-001 |

Do not sum both branches' capabilities as a single finished product. A future merge/rebase must resolve documentation/protocol conflicts and rerun checks on the exact resulting commit. Existing Draft PR #1 is not closed or merged by this work.
