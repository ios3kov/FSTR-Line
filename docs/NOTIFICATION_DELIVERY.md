# SYNC-001 delivery contract — 2026-09-29

Status: implementation stage, not a production subscription. Baseline:
`1d31eede4b32a4a57d8ababe3ad451ce4ffd353c`. Target remains AE 25.6.0.101,
macOS arm64, CEP 12. Existing Core/Host/UI boundaries remain unchanged.

## Decision and scope

Implement the read-side delivery state machine before attaching any private
producer. Actor: the open FSTR panel. It needs a current snapshot after an
AE-originated committed change, with no periodic discovery reads.

The existing research proves observation, not a callable subscription ABI.
`DoProcessProjectChanges` also fires in idle; its return alone must not be a
change event. An eventual producer must correlate actual mutation/context
signals with a verified committed boundary. No private addresses, detours,
debugger, idle polling, timer polling or unverified event name are installed by
this stage. No notification source is added to the CEP entry point yet.

The `read()` transport contract must settle only when its host operation has
ended. Use `CEPAdapter.readNotificationSnapshot()` for this contract; it retains
the pending Promise until the actual callback even after the normal read
deadline. `readSnapshot()` still rejects promptly for the existing UI and must
not be plugged into this module directly. The adapter refuses additional host
calls while completion is unknown. If a callback never arrives, the delivery
deadline blocks the session; recovery needs verified host termination/restart,
not a new adapter instance. No live source is wired to this path yet.

This module is an integration prerequisite, not acceptance of the source or
its claimed post-commit semantics. It cannot detect a final silently lost event
when no later event arrives. Sequence numbers detect only observable gaps.

## Requirements and acceptance

| ID | Requirement | Automated acceptance |
| --- | --- | --- |
| ND-01 | Refuse unknown protocol, build, host binary identity or missing committed-delivery capability before reading | Each identity field mismatched; no reads; explicit new matching session recovers |
| ND-02 | One initial read per explicit open/reconnect; no reads without new notifications thereafter | Initial read settles; no work queued in idle |
| ND-03 | Validate bounded messages; exact session and monotonically increasing positive safe-integer sequence | Invalid messages fail closed; old-session messages cannot affect current session; duplicates are ignored |
| ND-04 | At most one read in flight; bursts use a dirty bit, not an unbounded event queue | Thousands of notifications during one read yield one trailing read; obsolete result never publishes |
| ND-05 | A sequence gap or explicit overflow invalidates the projection and reconciles by snapshot | Gap/overflow publishes only reconciled state, counts detected gaps |
| ND-06 | No-op/cancelled/failed operations produce no refresh unless producer declares state changed | Explicit no-op sequence advances without reading; partial change is a changed event |
| ND-07 | Read failure stops automatic work; explicit new handshake/recovery is required | No retry loop even if more events arrive; late replies ignored |
| ND-08 | Close/reconnect invalidates pending results and releases retained event work | No publication while closed; reopen while old read pending remains serialized |
| ND-09 | Snapshot reads have a bounded deadline; unknown in-flight host work is not overlapped after timeout | Timeout blocks this instance; recovery requires new transport after old operation has settled or host restart |

Identity is a compatibility check, not authentication. The caller must supply
locally verified identity from a trusted producer; a CEP message cannot grant
itself compatibility. The allowlist is provided by the integration, never by
the event. No production allowlist is approved in this stage. It must bind AE
version/build, architecture, loaded BEE and AfterFXLib identities and matching
panel/producer build ID. A reconnect must use a fresh opaque session ID.

Each event is either `changed` (producer has verified post-commit state),
`noop`, or `overflow`. Failed/cancelled operations that partially change AE
state MUST emit `changed`; error does not imply rollback. Unknown commit phase
fails closed. Notifications carry no code, paths, project content or addresses.

## Verification planned before implementation

Run TypeScript/Core/adapter tests, dedicated state-machine tests with deferred
reads and an injected deadline scheduler, CEP build/host syntax/runtime tests,
package integrity and research regression. Review lifecycle interleavings and
run the local static scanner. Commit the completed stage, then repeat the
applicable build/tests against that commit. No distributable candidate is
delivered by this stage.

Actual shipping producer: BLOCKED pending an admissible in-process source and
compatibility/safety/maintenance/licensing decision. Real AE post-commit matrix,
silent missed-event detection, native no-op/error/cancel, native panel-closed
resource behavior, uninstrumented CPU/memory/playback comparison and supported
platform matrix: NOT RUN for this consumer-only stage. Unit evidence cannot
close these gates. AE is locally installed, but there is no producer to test.

Rollback: revert the standalone delivery module/tests/docs; existing CEP runtime
does not import it and retains its current behavior.
