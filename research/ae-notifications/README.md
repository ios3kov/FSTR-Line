# Isolated AE notification research

This directory is NOT part of the CEP package. SYNC-001 remains mandatory: the complete required native UI/script/other-plugin change stream must reach the panel without periodic layer/revision/idle polling or focus dependency. One internal channel is not required if multiple proven AE-originated channels provide complete coverage. No concrete internal candidate has been identified in this environment.

## Rules and research decision

DEVELOPMENT_RULES.md does not categorically forbid private-hook research. Sections 3, 4, 13-16, 20-22 and 26 apply. The user's 2026-09-28 instruction authorizes isolated internal research; it does not accept an unstable hook as a production solution. Earlier supported-public-API-only text describes the prior research track, not a universal prohibition. Private integration needs a separate compatibility, safety, maintenance and applicable licensing review before distribution. Never infer impossibility from incomplete public APIs or from unavailable local binaries.

## Stage A: exact binary identity and static leads

Read one explicitly selected executable/dylib/framework binary, not the whole application directory:

```sh
python3 -B research/ae-notifications/inspect_binary.py "$EXACT_AE_BINARY" \
  --ae-build 25.6.0.101 --output "$OWNED_RESEARCH_OUTPUT"
```

The Python 3.10+ tool reads only, never executes/modifies the binary, records SHA-256, Mach-O slices/CPU/UUID, matching symbol-table names and bounded printable leads. Each report is placed in a unique directory and records the script hash. The supplied AE build label is explicitly an unverified claim; correlate it with the application's version and loaded module UUIDs. Repeat for the actual loaded modules, which may contain the implementation outside the main executable. Do not upload Adobe binaries to this public repository.

Defaults: 2 GiB maximum input, first 256 MiB string scan, 200 matching string/symbol leads and at most 200,000 symbol entries per slice. All truncation is flagged. Stripped symbols, no matches or partial scans do NOT establish that an event path is absent. This tool does not perform disassembly/cross-reference analysis; that is the next evidence-producing step using the exact identified modules. Function-looking names or symbol addresses do not establish a callable ABI.

## Stage B: candidate-specific supervised tracing

Prerequisites: the exact licensed AE 25.6 build, disposable empty project, independent action oracle, an explicitly approved test-process PID, debugger permissions, identified candidate functions and their modules. Do not attach to the user's live work session. Do not disable SIP, re-sign AE, change security settings/preferences or kill a pre-existing process to make tracing work. If permissions prevent it, record BLOCKED and retain evidence.

`trace_callback.py` is an opt-in LLDB breakpoint callback logger. It does not attach, create any breakpoint, install a hook, dereference candidate arguments or evaluate code in AE. The researcher first locates a concrete symbol/address from real evidence and creates an explicitly scoped breakpoint. Then import this module through LLDB's `command script import`, call `start_capture(path, run_id, expected_pid, {module_uuid: sha256}, ...)`, and associate `trace_callback.on_breakpoint` with that specific breakpoint using `breakpoint command add -F`. UUIDs/hashes/PID must come from this run, never guessed examples.

A callback records timestamp, thread, module UUID, unslid location and breakpoint identity. The logger validates PID and UUID but cannot independently validate that a supplied UUID/hash mapping came from the same bytes; correlate it with Stage A and loaded-image evidence. Function names are bounded by the concrete module's debug metadata. Hits are labelled candidate-hit, never Timeline notifications. `commitPhase` stays UNKNOWN. No target memory, keys or user project names are captured by this logger.

A normal callback returns False (LLDB continues); a PID/module mismatch, error or capture limit returns True (LLDB pauses). The bounds are checked on callback delivery, not by a background timer. This is a SUPERVISED test, not an unattended recorder. End the capture explicitly with `stop_capture()`, remove only owned breakpoints and detach under debugger control. The tools do not automate process lifecycle. Native LLDB execution is NOT RUN here; tests cover the Python contract with fake frame objects.

## Stage C: prove source and post-commit semantics

1. Establish a positive control: a known action reaches the measuring mechanism. The existing command probe's loaded record is not that control.
2. Execute one isolated operation per run, record independent before/after state and the native/script/plugin action ID; distinguish wall-clock and monotonic clocks.
3. Prove whether the path publishes model changes or merely handles input/drawing/menu updates. Include native drag/trim, switches/selection/playhead, Undo/Redo and script/plugin-originated mutations; use coverage.json.
4. Identify each needed channel and payload/ABI from evidence; observe missed, duplicate, coalesced and reordered delivery. Function entry or timestamp proximity does not prove post-commit state. A callback which precedes mutation requires a proven completion channel, not timer polling.
5. Only then implement a separate candidate-specific diagnostic probe. Do not invent offsets, layouts, symbols or listener names. The old AEGP command probe remains a partial measuring instrument, not the solution.
6. Repeat restart/save/reopen/cancellation/error/no-op cases. Measure uninstrumented baseline separately from debugger runs: breakpoint overhead is not production latency. Record CPU, memory, stalls, idle state reads and playback impact before proposing production integration.

## Acceptance and evidence

Each matrix row needs exact AE/module/probe identity, input, independent expected changes, delivered channel/correlation IDs, post-commit evidence, missed/duplicate events, status and limitations. No supported origin/field may be silently dropped; N/A requires an explicit technical explanation and must not narrow the product requirement. Full sync, native compatibility, post-commit behavior and performance remain NOT RUN/BLOCKED until actual tests exist. Multiple channels are acceptable only as a tested union. Finding an internal path is progress, not automatic production acceptance.

The 2026-09-28 command priority interpretation is corrected in docs/TEST_RECORDS/COMMAND-PROBE-ERRATA-2026-09-28.md; historical logs are retained unchanged.

## Primary references

- LLVM Mach-O definitions (header/layout constants; consulted 2026-09-28): https://llvm.org/doxygen/BinaryFormat_2MachO_8h_source.html
- LLDB tutorial (explicit breakpoint/module scoping): https://lldb.llvm.org/use/tutorial.html
- LLDB breakpoint Python callback and return behavior: https://lldb.llvm.org/use/tutorials/breakpoint-triggered-scripts.html
- LLDB address API: https://lldb.llvm.org/python_api/lldb.SBAddress.html

The parsers/logger are original project code; no Adobe binary or proprietary SDK content is redistributed. LLVM/LLDB references describe tooling, not an AE event API.
