# Notification session replay regression — 2026-09-29

Scope: read-side notification delivery only; no native producer or panel wiring.
Target source commit: `7a35a71f883dc4ef23d9ad9c2ec7b15c733564aa`.
Environment: macOS arm64, Node 24.12.0, AE runtime not used for this unit gate.

The consumer retained only the immediately preceding session ID. A producer
that reopened `session-1`, then `session-2`, then `session-1` could make old
events match the current session again. A regression test reproduced this:
expected refusal, actual `open()` returned true; targeted test exit 1.

The consumer now retains accepted IDs in a bounded per-instance set. It
refuses any ID already accepted and refuses additional reconnects after 1024
unique sessions. Recreating an instance resets that local history; the trusted
producer must still supply fresh unguessable IDs and authenticate the channel.
This change does not make an untrusted handshake trustworthy.

| Gate | Result | Evidence |
| --- | --- | --- |
| Replayed session after intervening session | PASS after fix | New ND-03 regression test |
| Bounded session history | PASS | New 1024-session refusal test |
| `npm run check` | PASS | 71 TypeScript tests, build exit 0 |
| `npm run check:cep` | PASS | Clean build `fstr-cep-7a35a71f883d`; host syntax and CEP packaging |
| `node --test tests/runtime/*.test.mjs` | PASS | 38 runtime/package tests against clean source |
| Research suite | PASS | 113 tests; printed FAIL/BLOCKED fixtures are expected negative-case output |
| Static code scan | Review required, exit 1 | Three pre-existing `eval` heuristics in bridge/generated CEP, no finding in changed module |
| Real AE producer, direct delivery, post-commit and performance | NOT RUN | No accepted shipping producer |

The module remains unconnected to the CEP entry point. SYNC-001 production
acceptance remains blocked on a safe, complete AE notification source and the
remaining real-runtime gates. This regression closes only local session replay
within one delivery instance.
