# After Effects SDK 25.6 header audit

- Run: `FSTR-SDK-25.6-HEADER-AUDIT-2026-09-28-01`.
- Target: After Effects 25.6.0.101, Mac OS SDK downloaded from Adobe Developer Console.
- Archive: `/Users/os3kov/Downloads/AfterEffectsSDK_25.6_61_mac/ae25.6_61.64bit.AfterEffectsSDK.tar.zstd.zip`.
- Archive SHA-256: `e02fa2b488c3cceb238866b648eb9a2526d308a260744367915a2f173663c36c`.
- Extraction: PASS. The archive is Zstandard-compressed tar data despite the `.zip` suffix. Header/text source files were extracted to `/private/var/folders/bs/39klz7cd52z6xkm817vj0zjm0000gn/T/opencode/fstr-sdk-25.6-audit`.
- Primary header: `Examples/Headers/AE_GeneralPlug.h`.

## Findings

The AEGP Register Suite exposes:

- `AEGP_RegisterCommandHook`: command interception, including `AEGP_Command_ALL`;
- `AEGP_RegisterUpdateMenuHook`: called before menus are drawn;
- `AEGP_RegisterIdleHook`: sporadic idle callback with a requested sleep interval;
- lifecycle/about/version registration hooks.

No registration function for native Timeline, project, layer, selection, playhead, or Undo/Redo change notifications was found in the official headers. The SDK examples register command and idle hooks but do not demonstrate a complete project-change event stream.

The Render Suite exposes `AEGP_GetCurrentTimestamp` and `AEGP_HasItemChangedSinceTimestamp`. Header comments scope these to changes affecting rendering and video changes of an item. They are synchronous queries made by a caller; they do not notify a panel and do not cover the required non-rendering Timeline state.

## Gate result

- Version-pinned header inspection: **PASS**.
- Direct push notification API covering SYNC-001: **NOT FOUND**.
- Native runtime probe: **NOT RUN**; there is no candidate callback to probe.
- C++ implementation decision: **not justified for SYNC-001** based on this SDK.
- Existing CEP/ExtendScript implementation: unchanged.

This record does not weaken or remove the mandatory product requirement. It establishes that adding a native plugin solely to obtain the required direct notifications is not supported by the inspected public AE 25.6 SDK surface.
