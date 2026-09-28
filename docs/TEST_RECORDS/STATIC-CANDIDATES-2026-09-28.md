# Static candidates from real AE 25.6.0.101 modules — 2026-09-28

Input: FSTR-AE-Static-20260928T213703Z-cd1461c05b83.zip, SHA-256 806bbef5a272548a1825c7a4dc3f200705b6b3ed76274dc99b6868ee4e20f4a9. AE 25.6.0.101 was identified. 256 real Mach-O modules were read successfully; overall collection is BLOCKED because the module/time/byte budget was reached, so it is not a whole-application scan.

Strongest AE-specific static leads:
- BEE.dylib (SHA 817b9de9c6d57b5d6988b634842090e1528fe817a5685c8d1ff358553c6660ca, UUID 161300f3-73f8-3ebc-a751-959df40a073b): defined nlist names for BEE_Layer::CmdPreParamChange and BEE_Layer::CmdParamChanged; strings for BEEp_CLayerDispatcher, BEEp_CProjectDispatcher and BEE_Selection.
- AfterFXLib (SHA ce3aa2f16fe5449a77379a6b622e1a221596e511b86f7708dd3e2f7a3cced01a, UUID edc800d6-9e4b-3a03-9bbb-8239f3f6eea5): dvacore::messaging::Signal involving BEE_UndoContext, BEE_Selection, LifetimeObserverToken and ProjectSettingsChanged messaging.
- Main executable ProcessBeginEndNotificationRegistry is lower-priority for Timeline mutation coverage.

These are static leads, not a notification source. They do not prove direction, post-commit timing, completeness, stability, or a callable private ABI.

Focused gate e5e0bbc initially attempted LLDB disassemble by the raw Mach-O nlist spelling and the owned macOS smoke correctly failed. That spelling includes platform/linker conventions and is not accepted as proof of LLDB's function name. The gate was narrowed: exact SHA + native nm + LLDB image lookup are required first; no disassembly/runtime breakpoint is created until a resolved lookup identity is observed. Historical FAIL is retained.

Next: run the corrected focused static kit on the same exact AE modules. If lookup identities corroborate the report, create candidate-specific runtime tracing and test native UI, ExtendScript and plugin-originated changes across timing/layers/selection/switches/context/playhead/Undo/Redo, including post-commit state, duplicates, misses, restart and performance. Polling/revision/idle/focus/self-events remain unacceptable substitutes.
