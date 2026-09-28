# Command probe interpretation correction — 2026-09-28

This additive erratum corrects the interpretation in COMMAND-PROBE-RUNTIME-2026-09-28.md without rewriting its historical log.

The only observed record in the cited run had kind=loaded. In source a7cee2ce4fdc22906da03ee32c2c2f0c17188c4d, EntryPointFunc calls log_event(..., err, 0, FALSE). Therefore its priority=0 is supplied by the probe itself. It is NOT evidence that AE delivered callback priority 0, nor evidence of before/after-commit semantics. The reported priority discrepancy was not established by that record.

The corrected logger separates synthetic lifecycle/status rows (isCommandCallback=false, command/priority/alreadyHandled=null) from actual command-hook rows (isCommandCallback=true, supplied priority). Limits retain run build identity. Registration failure closes the log handle. A Linux C++ logger-only harness compiles and executes the actual formatter prefix; it does not compile against the Adobe SDK or load the plugin in AE.

The original negative observation remains: no command callback was observed for the tested ExtendScript mutation. No native UI positive-control callback was recorded, so the test does not by itself distinguish coverage limitations from an instrumentation/registration issue. Before interpreting further absences, prove callback delivery with a known command through the same instrumentation, then repeat every required native/script/plugin scenario.

Current native SDK build, installation, actual callback delivery, post-commit timing and complete SYNC-001 coverage: NOT RUN/BLOCKED in this environment. No internal candidate is invented and no product notification source is claimed. See research/ae-notifications/README.md for the separate internal-research track.
