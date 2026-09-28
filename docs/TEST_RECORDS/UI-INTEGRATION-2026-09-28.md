# Read-only UI and bridge integration — 2026-09-28

Baseline: host/package commit 225671d36552bb0428e7487e0288ab28ea4cf301, whose Integration gate passed (run 36475002085). No AE runtime execution follows from that result.

## Implementation and planned verification

The donor branch's visual-lane approach is adapted to the canonical typed snapshot rather than importing its incompatible host/UI contracts. The panel shows real layer names and proportional clip ranges, selection state and disabled state. This is read-only; editing widgets, drag, snapping, playhead controls, exact label palette and virtualization remain deferred.

The view now renders the last-known projection on a failed refresh and marks it STALE. The controller keeps this projection across subsequent failures, but discards it on a confirmed NO_ACTIVE_COMP or explicit invalidation. Tests cover the rendered DOM contract, not just the controller state. Error snapshots are never presented as current AE truth.

The bridge latches uncertain mutation outcomes after timeout, empty/malformed response, wrong operation identity or rollback/recovery failure. A later successful read does not authorize retrying the possibly applied write. Ordinary structured preflight rejections allow a later explicit command. The latch is not a global guarantee across extension reload; native state must be inspected and the host/bridge restarted before continuing after uncertainty. No automatic mutation retry is added.

The existing two-second prototype is explicitly labelled Experimental polling and remains disabled by default; it is not SYNC-001 and is not its fallback acceptance path.

## Level 1 commands

npm ci; npm test; npm run check:cep; node --test tests/runtime/*.test.mjs; node scripts/verify-cep.mjs.

Added tests execute the compiled controller, renderer and bridge using a minimal DOM contract and a modeled transport. GitHub Actions on the exact commit records PASS/FAIL. Browser/CEP rendering, real After Effects editing/Undo and complete notifications remain NOT RUN/BLOCKED until the native test environment is available. Do not call this a completed editor or full donor-branch integration.
