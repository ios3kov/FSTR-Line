# Owned composition completion trace — 2026-09-29

User explicitly authorized creating a test composition and temporarily attaching
the debugger to their launched AE session. No user composition was modified,
no project was saved/closed, no restart, preference change or plugin install.

Source: clean 1a83dbdcf58a98f6d8273676473d5e6d9f98de7a.
Run: completion-ov1bj46q. AE 25.6.0.101, macOS arm64, PID 30059.
On-disk BEE hash and loaded module UUID verified; all eight breakpoints resolved
to exactly one location. Pre-run Python research suite: 108 tests PASS.

Owned fixture: `FSTR completion test 19f5fb025c94`, comp ID 1, layer ID 15.
It remains in the project, with layer enabled=true. Runner checks its unique
name and IDs before each action. No automatic deletion or Undo was performed.

| Script window | Completion-edge hits | Signal-call-site hits | Final enabled |
| --- | --- | --- | --- |
| Two toggles in one group | 2 | 0 | true |
| Two toggles in separate groups | 4 | 0 | true |
| Assignment of existing enabled value in a group | 2 | 0 | true |

All edge hits were group-completion-edge. Example stack contains
SetExecutingCommandGroup → BEEp_EndGroup → BEE_EndGroup →
DVAAEScripting::ApplicationHelper::EndUndoGroup. Capture errors/limits: none.
Observer completed and clean detach: PASS. This is research instrumentation,
not shipping notification delivery. No private subscriber was installed.

Two hits per group are an unresolved observation, not assumed duplicates of
the same context: this logger did not capture context identity. Zero call-site
hits are consistent with the observed NumSlots guard, but do not demonstrate
subscriber delivery. No-op also reaching the edge confirms that an edge count
alone must not be treated as a successful mutation count.

Final states come from each action script, not a separate independent oracle.
Undo/Redo, error scenarios, post-commit ordering and uninstrumented performance
were not tested in this run. SYNC-001 production gate remains NOT RUN.

Evidence archive: FSTR-Completion-ov1bj46q.zip, retained in chat outputs.
SHA-256: `970c3942063251c81860ab6bba220ca3fac9da66f339ea9a6badf03abe840f24`.
Includes redacted plan, identities, actual scripts, results, trace and debugger
log; no AE project payload. Archive is local evidence, not a published release.

Next: distinguish context/thread identities for doubled edges, add independent
owned-fixture reads and bounded Undo/Redo/error scenarios. Keep runtime research
separate from safe private subscription ABI and shipping acceptance.

## Follow-up: context address distinction

Run `completion-gcokp48f`, clean source
`a0e507b1f9abf4326d9c7c60ee8eb2d979632b6f`, same exact AE build/PID.
Acceptance: distinguish doubled edges without logging pointer values or
dereferencing target memory; fail closed on unavailable registers; clean detach.
The exact-build arm64 sites preserve the context pointer in x19. Optional
register capture maps addresses to session-local tokens, not lifetime IDs.
110 Python research tests PASS, including token reuse/redaction and unreadable
register refusal. Live observer and detach PASS; no capture errors/limits.

| Window | context-1 / thread 14785181 | context-2 / thread 14785750 | Signal calls |
| --- | --- | --- | --- |
| Grouped | 1 | 1 | 0 |
| Separate | 2 | 2 | 0 |
| No-op | 1 | 1 | 0 |

All eight hits are group-completion-edge. Thus in this run the paired hits
belong to distinct context addresses and threads, not repeated hits of the same
address. Their semantic roles and object lifetimes are not established; do not
label them main/render contexts or treat these tokens as durable identities.

New owned comp `FSTR completion test cf59d1b55ebb`, ID 16, layer ID 29,
remains enabled=true per action-script results. The prior fixture was not
removed; this runner has now created two retained test comps. User comps were
not targeted. No save/close, Undo/Redo, native subscriber or plugin installation.
Independent oracle, error cases, shipping delivery and performance NOT RUN.

Evidence: `FSTR-Completion-gcokp48f.zip`, local chat outputs, SHA-256
`d45c96f07c135d7b679e636e8e4cd97822fbe9a5ac1aceba612b83d2ff6aec92`.
Contains redacted trace/scripts/identity/results and source-bound count summary.
Static code scan exit 1: three existing eval heuristic warnings in CEP bridge,
generated client and host JSON fallback; no finding in changed research scope.
This is not security certification. SYNC-001 production gate remains NOT RUN.

Next: independent owned-fixture state reads and controlled exception cleanup;
design isolated Undo/Redo without touching unrelated history. Do not infer
post-commit delivery from completion-edge observations.
