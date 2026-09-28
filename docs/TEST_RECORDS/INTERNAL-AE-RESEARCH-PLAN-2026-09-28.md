# Internal After Effects notification research plan — 2026-09-28

Status: planned; no internal AE mechanism has been identified or implemented.

## Objective

Determine whether After Effects 25.6 has an internal event-delivery path that
could explain Timeline/project notifications not exposed by the public SDK.
The result is exploratory evidence, not an automatic production solution.

## Scope and controls

- Target: AE 25.6.0.101 on macOS Apple Silicon.
- Use a disposable test project and unique Test Run IDs.
- Preserve the installed AE binary; do not patch or replace it.
- Keep all traces, probes, and artifacts outside production FSTR code.
- Use read-only observation wherever technically possible.
- Do not inspect or modify user projects, preferences, or third-party plugins.
- Stop immediately on crash, hang, project corruption, or unexplained global
  state changes; preserve the evidence before cleanup.

## Investigation sequence

1. Record AE binary identity, version, architecture, and hashes.
2. Inspect symbols, strings, and metadata for event-dispatch terminology related
   to project, Timeline, selection, playhead, and Undo/Redo.
3. Trace isolated operations with a debugger or equivalent read-only tooling:
   native edits, selection/switches, playhead, project changes, Undo/Redo,
   ExtendScript edits, and plugin-originated edits.
4. Correlate observed calls with state before and after each operation. Determine
   whether delivery is before commit, after commit, or unrelated to mutation.
5. If a concrete candidate exists, create a separate diagnostic probe that logs
   event identity, timestamp, origin scenario, and safe correlation data only.
6. Repeat the complete SYNC-001 matrix and record misses, duplicates, reload and
   restart behavior, crash/hang behavior, and performance impact.

## Acceptance gate

The research passes only if a candidate covers native UI, ExtendScript, and
other plugins for layer timing/add/delete/order, selection, switches, active
composition/project, playhead, and Undo/Redo. It must remain usable after
restart and must not require polling or unsafe memory assumptions.

Observation of an internal function alone is not a pass. Version-fragile,
undocumented, incomplete, or unsafe mechanisms remain research findings and are
rejected for production SYNC-001 until a separate compatibility, safety, and
maintenance decision is made.

## Current result

Not run. The public audit found no complete supported source; no private hook has
been identified, tested, or added to FSTR Line.
