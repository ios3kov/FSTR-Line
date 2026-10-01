# Real Context probe result and post-commit marker correction — 2026-09-29

Input: `FSTR-AE-Context-20260929T080541Z-208329837f6e.zip`, 11,762 bytes, SHA-256 `780327bb9297f69dc4473f565e2f9c2895ab8fa53c4172234a3d8735c48ec1e7`. Exact build `88b289612a6b734e12468675e0ac33cee1f4311f`. Runtime attach/setup/capture/clean detach PASS.

## Active composition — OBSERVED

The corrected owned-file state oracle worked on real AE and recorded:
- before comp-switch: `comp=Comp 1`
- after comp-switch: `comp=Comp 2`
- before comp-switch-back: `comp=Comp 2`
- after comp-switch-back: `comp=Comp 1`

Both switch windows contained exactly:
- `CItem::DeactivateVOut()` / `item-deactivate-vout`: 1
- `CItem::ActivateVOut()` / `item-activate-vout`: 1

Thus active-comp/view switching has a concrete exact-build direct internal candidate and is correlated with independently observed active-comp name transitions in both directions. The active-comp candidates were absent from the idle windows in this run.

State oracle itself is therefore OBSERVED on real AE. It also independently confirmed the timing edit: layer 2 changed from start/in/out `0 / 3.04 / 9.28` to `-1.68 / 1.36 / 7.60`.

## Background project-processing note

The first idle-control window contained two complete DoProcessProjectChanges entry/boundary/return cycles, while idle-after contained none. This reinforces that project-processing addresses are wake/work boundaries rather than one-event-per-user-mutation notifications.

## Marker failure

The screenshot/error and evidence identify a tooling defect, not an AE candidate failure:
`Unable to execute script at line 5. Function file.flush is undefined`.

`FSTR-PostCommit-Marker.jsx` used `File.flush()`, which is unavailable in the target ExtendScript File API. The AppleScript bridge returned successfully but the marker file contained no rows, so `postProcessing` correctly remained UNPROVEN.

Correction: marker timestamps are now collected in memory and written once using supported `open("w") → writeln → close`. No flush call remains. The next handoff is reduced to three windows only: idle → automatic marker-script → idle. Active-comp and general timing tests are not repeated.

SYNC-001 remains NOT RUN because post-commit and other-plugin provenance are still open.
