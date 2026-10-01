# Plugin-origin overlap run: direct channel observed, state preflight gap — 2026-09-29

Input: `FSTR-AE-PluginOrigin-20260929T085035Z-6fbcd36ebc06.zip`, 8,409 bytes, SHA-256 `1a444be0e63bfa35e88c06732681d8edfb338d43f527a460ef318277f7b82225`. Observer kit commit `5ee74569a385c655071aff1ec6fd5404e02900c4`. Runtime observer PASS/clean detach.

## What is now proven

The mutation-driven overlap protocol worked. Helper provenance in the action window:
- helper Build ID `fstr-plugin-origin-d5a86afe5448-20260929T084015Z`
- helper source commit `d5a86afe5448882429346a07da72eecea486c193`
- mutationEnd wallTimeNs `1790671832966457000`
- first layer VIDEO_ACTIVE `0 → 1`
- statusCode 0.

Direct exact-build observer hits in the same action window:
- `layer-switch-internal`: 2
- `after-process-from-render-thread`: 13
- `process-project-changes-return`: 13
- `end-group`: 4
- `render-end-undo-group`: 2.

Nearest timing around helper mutationEnd:
- layer-switch: -55.091 ms
- end-group: -26.350 ms
- end-group: -6.164 ms
- layer-switch: +15.845 ms
- after-ProcessFromRenderThread: +37.511 ms
- DoProcessProjectChanges return: +56.336 ms
- render-end-undo-group: +98.691 ms.

Thus independent AEGP plugin provenance and the direct internal change path are now temporally correlated in a single bounded action window.

## Why the full acceptance gate is still not marked PASS

The pre-action state oracle returned `NO_ACTIVE_COMP`. The post-action oracle returned `Comp 2` with L1 video active = 1. Therefore the helper's own 0→1 change and direct channel are observed, but an independent before-state value for L1 is missing.

The acceptance rule is not weakened. Observer v3 adds a preflight before LLDB attach:
- active comp must be present;
- L1 must be present and its video-active value must parse as 0 or 1;
- otherwise the run BLOCKS before tracing and instructs the user to click/open the test comp.

Final state acceptance now requires exact equality:
`snapshot before == helper beforeVideoActive` and
`snapshot after == helper afterVideoActive`,
plus an actual transition.

No helper rebuild/reinstall is required.
