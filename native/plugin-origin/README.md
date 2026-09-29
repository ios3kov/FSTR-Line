# FSTR Plugin Origin Probe

Diagnostic-only AEGP used to prove **other-plugin mutation provenance** for SYNC-001.

It adds one menu item: **Window → FSTR Plugin Origin Test**.

When invoked with an active composition containing at least one layer, it uses only public AEGP suites to:
1. get the active composition,
2. get its first layer,
3. read `AEGP_LayerFlag_VIDEO_ACTIVE`,
4. open an undo group,
5. toggle that flag with `AEGP_SetLayerFlag`,
6. close the undo group,
7. read the flag again.

It writes a process/build-specific provenance JSONL file under `/tmp`:
`FSTRPluginOrigin-<AE pid>-<Build ID>.jsonl`.

This helper is not production FSTR code. It does not use private AE functions, polling, background threads, scripting, network access or external process control.

Build must use the exact AE 25.6 SDK on macOS. Installation/restart and the separate observer are explicit test steps.
