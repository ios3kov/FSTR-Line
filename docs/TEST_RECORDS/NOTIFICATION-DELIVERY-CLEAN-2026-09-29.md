# Clean-source delivery verification — 2026-09-29

Run ID: `ND-20260929-02`. Tested implementation commit:
`fcf1cacd5df5cce95ca798a9c08e8649b557b903` (clean worktree).
Build ID: `fstr-cep-fcf1cacd5df5`. Environment: macOS arm64,
Node 24.12.0 / npm 11.6.2 / Python 3.14.2.

| Command | Result | Evidence |
| --- | --- | --- |
| `npm test` | PASS, exit 0 | 62 tests, including 17 delivery tests |
| `npm run check:cep` | PASS, exit 0 | Clean-identity CEP bundle and host syntax |
| `node --test tests/runtime/*.test.mjs` | PASS, exit 0 | 34 tests, including negative package integrity cases |
| `node scripts/verify-cep.mjs` | PASS, exit 0 | Exact payload, hashes, clean identity |
| `git status --short` | PASS | Empty after build and tests |

CEP manifest SHA-256:
`cdfcc6ffc53ce7f2edd4be638622c49730c15eca292f25153117ef4566c527e6`.
The manifest identifies payload hashes. This is internal build verification,
not a delivered/installable release or proof of a loaded AE runtime version.

The dirty-package failure from `ND-20260929-01` is resolved by building the
committed sources; the integrity check was not weakened. Research regression
from that run remains applicable: those sources were unchanged, 91 tests PASS.

No actual AE notification producer is connected. All real-AE shipping,
performance and private-mechanism gates retain the statuses in
`NOTIFICATION-DELIVERY-2026-09-29.md`. The new delivery tests exercise synthetic
events and host replies; none is labeled real-AE evidence.

This record is added in a separate documentation commit so the tested
implementation and its build identity remain unambiguous.
