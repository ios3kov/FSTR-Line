# Plugin-origin final state/direct correlation — 2026-09-29

Input: `FSTR-AE-PluginOrigin-20260929T090335Z-1a2a1e564b15.zip`, 7,268 bytes, SHA-256 `dad9249991e0383b752c06cf960052fd5ca611c8ad47e9ae175d48abefcc4068`.

Observer kit:
- source commit `317f2d4517f3f81e1f0cb5c73c66c16e2fa6ff40`
- Build ID `fstr-plugin-origin-kit-317f2d4517f3`
- clean source state.

Installed independent diagnostic AEGP helper:
- Build ID `fstr-plugin-origin-d5a86afe5448-20260929T084015Z`
- source commit `d5a86afe5448882429346a07da72eecea486c193`
- binary SHA-256 `609d40e8cbc5d3e780c915933d62e6f3b16b469f2f15b7dc0539b7e5c77e8bfe`
- public AEGP SDK mutation path only.

## Acceptance result — PASS

Preflight snapshot before:
- active comp: `Comp 2`
- L1 video active: **1**.

Helper provenance mutation inside the bounded action window:
- mutationEnd wallTimeNs: `1790672612808044000`
- L1 `VIDEO_ACTIVE 1 → 0`
- statusCode 0.

Independent snapshot after:
- active comp: `Comp 2`
- L1 video active: **0**.

Therefore the independent state oracle exactly matches the helper's own before/after values.

Direct exact-build observer hits in the same action window:
- `BEEp_SetLayerSwitch` / layer-switch-internal: **2**
- `BEE_EndGroup`: **4**
- after-`ProcessFromRenderThread` boundary: **3**
- `DoProcessProjectChanges` return: **3**
- render-end-undo-group: **2**.

Action window duration: ~10.156 s. The current helper mutation occurred ~8.602 s after start and the observer remained active ~1.555 s after mutation.

Nearest exact hits relative to helper mutationEnd:
- layer-switch: -69.703 ms
- end-group: -29.664 ms
- end-group: -6.256 ms
- layer-switch: +23.131 ms
- after-ProcessFromRenderThread: +46.581 ms
- DoProcessProjectChanges return: +74.922 ms
- render-end-undo-group: +115.320 ms.

Most importantly, the first layer-switch stack contains:
`BEEp_SetLayerSwitch → BEE_CmdSetLayerSwitch → mutate_first_layer() [FSTRPluginOrigin] → command_hook [FSTRPluginOrigin] → AEGPDriver → SendCommandToPlugins [AfterFXLib]`.

This proves the direct BEE layer-switch path was reached by an independently compiled AEGP plugin mutation, not merely by native UI or ExtendScript timing correlation.

## Scope

The **other-plugin origin research gate is OBSERVED/PASS** for the tested public-SDK AEGP mutation.

This does not approve a production private hook. LLDB breakpoints are measuring instrumentation, not a shipping notification mechanism. Production acceptance still requires:
- a defined compatibility/safety strategy for internal/private delivery;
- post-commit read semantics for the actual shipping mechanism across required change families;
- duplicate/coalescing/missed-event behavior;
- panel-closed/error/no-op behavior;
- uninstrumented CPU/memory/playback responsiveness comparison;
- version/change detection and failure-safe behavior.

SYNC-001 therefore remains NOT RUN as a production integration gate even though native UI, ExtendScript and independent plugin origins now all have real research evidence.
