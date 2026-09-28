# Static candidates from real AE 25.6.0.101 modules — 2026-09-28

Input report: FSTR-AE-Static-20260928T213703Z-cd1461c05b83.zip, SHA-256 806bbef5a272548a1825c7a4dc3f200705b6b3ed76274dc99b6868ee4e20f4a9. The collector identified AE 25.6.0.101 and read 256 Mach-O modules (all module reads PASS) before its module/time/byte budget stopped further enumeration. Therefore the overall report is BLOCKED/incomplete, not a whole-application static PASS.

Strongest AE-specific static leads in the covered set:

1. Contents/Frameworks/BEE.dylib — SHA-256 817b9de9c6d57b5d6988b634842090e1528fe817a5685c8d1ff358553c6660ca, UUID 161300f3-73f8-3ebc-a751-959df40a073b. Captured defined symbols include BEE_Layer::CmdPreParamChange(TDB_StreamIDPath const&) and BEE_Layer::CmdParamChanged(TDB_StreamIDPath const&, T_Time const&). Strings also expose BEEp_CLayerDispatcher, BEEp_CProjectDispatcher, BEE_Selection and many layer setters. This is consistent with model mutation plumbing, but does not prove callback direction, completeness, or post-commit delivery.
2. Contents/Frameworks/AfterFXLib.framework/Versions/A/AfterFXLib — SHA-256 ce3aa2f16fe5449a77379a6b622e1a221596e511b86f7708dd3e2f7a3cced01a, UUID edc800d6-9e4b-3a03-9bbb-8239f3f6eea5. Captured names include dvacore::messaging::Signal involving BEE_UndoContext, BEE_Selection, U::LifetimeObserverToken and MessageNameForProjectSettingsChangedMessage. This is evidence that AE contains internal messaging/observer primitives; it is not yet evidence of a single Timeline change bus.
3. The main executable exposes dvacore::config::ProcessBeginEndNotificationRegistry, but this appears process/config related and is lower priority for Timeline mutation coverage.
4. Many third-party frameworks contain generic Notification/Layer/Selection names; they are excluded from the initial candidate set unless later call-graph evidence connects them to AE model mutation.

Current hypothesis to test, not a conclusion: BEE layer mutation functions may sit near the common model-change path, while AfterFXLib/dvacore messaging may carry higher-level selection/Undo/project notifications. A union of channels is acceptable only if the complete SYNC-001 matrix is proven.

Next gate: corroborate the exact symbols with native nm/LLDB static lookup/disassembly on the same module hashes, then create candidate-specific runtime breakpoints only after the static addresses and module identity agree. Runtime must prove native UI + ExtendScript + other-plugin origins, post-commit state, move/trim/layer structure/selection/switches/context/playhead/Undo/Redo, duplicates/misses/restart/performance. Polling and revision checks remain unacceptable substitutes.

No private hook has been implemented. No claim is made that these functions are stable APIs, safe to call, or sufficient for production.
