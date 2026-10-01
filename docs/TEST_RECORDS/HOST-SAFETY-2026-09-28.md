# Host safety implementation — 2026-09-28

Scope: integration/host-safety-notifications. Baseline: main 15d995e5d27140690c1966f14b2aa0029989a072. Applicable rules: baseline, Level 1, Undo safety, bounded recovery, clean identity; no native runtime acceptance claimed.

## Changes

- Move uses absolute targets captured before setters, avoiding repeated in/out translation under the coupled-setter model.
- Preflight precedes writes; rollback touches only planned properties on attempted targets, continues after individual restoration failures and checks resulting values.
- Incomplete rollback or uncertain Undo closure disables subsequent host writes. Read-only diagnostics remain available. Undo groups are not treated as transactions.
- No-op commands do not create an Undo group.
- Opaque revision compares exact observed state, project and composition references; includes selection, labels, names and playhead. It is not polling or an event source. Actual AE object-wrapper lifetime semantics must be tested.
- JSON2 from donor commit 2cfb93f is embedded in a private host closure, with notices; no dependency on global JSON.
- Explicit allowlisted package at dist/cep, clean commit identity, exact file-set and SHA-256 verification. Browser target is explicitly Chrome 88; target compatibility is not thereby proven.

## Reproduction and automated gate

The original host bytes were checked against Git blob bc7719ca9ce19b9171e9857b53246a9344a89e14.
The 22 new host regression assertions produced 3 PASS / 19 FAIL against that baseline, then 22 PASS / 0 FAIL against the local patched source in Node 22.16.0/Linux. These are fault-injecting model tests, not After Effects. The GitHub commit's authoritative results are its Integration gate run, including all pre-existing tests and the exact packaged-host JSON/integrity tests.

Commands: npm ci; npm test; npm run check:cep; node --test tests/runtime/*.test.mjs; node scripts/verify-cep.mjs.
A baseline CI run on 5d9b457e986219eec9d413ad041a70aaf7a5c72a passed: https://github.com/ios3kov/FSTR-Line/actions/runs/36473878880 . This validates the baseline's automated scope only.

## Open gates

Actual AE timing, keyframes/stretch/remapping behavior, safe wrapper identity, complete failed-write recovery, true Undo/Redo and performance remain BLOCKED without the AE test host. Arbitrary subframe timings remain explicitly unsupported; the implementation refuses them rather than silently rounding. Editing UI is not enabled on the basis of these model tests. Full direct notifications remain an independent mandatory gate.

No merge, release or installed AE change was performed by this stage.
