# Other-plugin provenance helper design — 2026-09-29

PostCommit script-origin positive control is already OBSERVED. The remaining SYNC-001 origin gap is an independently attributable plugin mutation.

A diagnostic-only AEGP helper is added using public SDK suites only. It registers **Window → FSTR Plugin Origin Test**. When explicitly clicked with an active comp, it toggles the first layer's `AEGP_LayerFlag_VIDEO_ACTIVE` via:

`GetActiveItem → GetItemType → GetCompFromItem → GetCompNumLayers → GetCompLayerByIndex(0) → GetLayerFlags → StartUndoGroup → SetLayerFlag → EndUndoGroup → GetLayerFlags`.

The helper writes its own PID/build-specific JSONL provenance file under `/tmp`, containing Build ID, wallTimeNs, before/after video-active values and status. It uses no private functions, ExtendScript, network, threads or polling.

The handoff kit has explicit stages:
1. `Build-Install.command`: user selects an extracted exact AE SDK. Source is copied into Adobe's Commando sample project and compiled arm64. Build is ad-hoc signed. Installation to Adobe Common MediaCore requires an explicit terminal confirmation + sudo. Existing non-FSTR plugin at the destination is never replaced.
2. User manually restarts AE.
3. `Observe.command`: validates exact AE 25.6.0.101, installed helper receipt, matching helper load log, exact BEE SHA, then observes one explicit helper menu mutation.
4. Acceptance requires matching helper provenance mutation, independent state-oracle first-layer video switch, direct `BEEp_SetLayerSwitch` hit plus project-processing boundary/return in the same action window, clean detach and matching Build ID.
5. `Uninstall.command`: removes only a plugin carrying a valid FSTR diagnostic receipt and requires explicit confirmation + sudo.

CI cannot establish Adobe SDK compilation. It separately compiles the exact C++ source against ABI-shaped fake suites and tests package scripts/observer analysis. Real exact-SDK compile/load remains a user-machine gate.

No production FSTR plugin or private-hook integration is introduced by this helper.
