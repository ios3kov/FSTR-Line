# Command probe build — 2026-09-28

Scope: isolated diagnostic AEGP; target AE 25.6.0.101, macOS arm64.
Acceptance for this step: reproducible compilation, correct executable metadata,
exported entry point, signature verification, unique build evidence. Runtime
acceptance additionally requires actual loaded Build ID and operation matrix.

## Results

- Build `20260928T183240Z-cf383a8-71368`: PASS (working source over cf383a8;
  exact source hashes and Git state in the build directory).
- Xcode 27.0 / 27A266a, official AE SDK 25.6 headers and Commando build template.
- Architecture: arm64; deployment target macOS 12.0.
- EntryPointFunc export: PASS.
- Ad-hoc signing and strict signature verification: PASS.
- Bundle executable metadata corrected from SDK template's hard-coded Commando.
- Artifact and evidence: `.artifacts/command-probe/20260928T183240Z-cf383a8-71368/`.
  `SHA256.txt` identifies the ZIP; `source-sha256.txt` identifies inputs;
  `xcodebuild.log` contains compilation output. Local evidence, not published storage.
- Install / AE load / native operation smoke: NOT RUN. AE is already running
  (observed PID 68154); capture requires a new AE process with a unique log path.
- Coverage and performance: NOT RUN; SYNC-001 remains BLOCKED.

Earlier attempts failed due to missing copied header, ERR macro local variable,
template executable metadata, and a seven-argument entry point copied from the
outdated Commando sample rather than the five-argument SDK prototype. The ABI
mismatch caused an invalid plugin ID. AE displayed `5027:47 Plugin ID is
invalid`; that runtime attempt is INVALID and is not evidence about hook
coverage. These were preparation/code defects, not host API findings. A successful
compile was not established before those corrections.

## Runtime protocol (required, pending)

Use a disposable test project and a new run directory. Confirm installed bundle
hash and the log's loaded Build ID before testing. Mark each action externally
with timestamps, capture before/after AE state, and correlate with command logs.
Test native move/trim, add/delete/reorder, selection, switches, comp activation,
project open/new, playhead/scrub/playback, Undo/Redo, script edits and plugin edits.
An enclosing Run Script command is not evidence of per-mutation notification.
Missing records are inconclusive until positive-control commands are observed.
Report actual callback priority; do not infer post-commit timing from AfterAE.
Use bounded launch/load waiting and report crashes/hangs explicitly. The capture
limit in the plugin is not a host watchdog. Compare responsiveness and playback
with baseline separately; synchronous diagnostic log flushing has overhead.

Failure of this candidate does not prove absence of every possible public API.

## Runtime follow-up

First runtime build produced registration error 3 and user-visible 5027:47.
Do not attribute this to AfterAE: the entry point ABI was wrong. The MediaCore
location hypothesis was also unproven. The trial user-directory installation
produced no log within 90 seconds; loading there is not established.

Corrected build `20260928T184359Z-cf383a8-72414` compiles with a static assertion
against `AEGP_PluginInitFunc`, exports EntryPointFunc and passes strict signature
verification. Requested priority is BeforeAE and the log now agrees. Runtime
of this corrected build is NOT RUN: AE remained running after a guarded scripted
quit attempt; a subsequent diagnostic AppleScript request timed out. This is an
automation timeout, not proof of an AE hang. The old user-directory probe remains
installed pending orderly shutdown and replacement. The MediaCore copy was removed.
