# Direct event source: received modules and dirty-signal discriminator

Test Run ID: `DIRECT-SOURCE-20260930-01`. Date: 2026-09-30.
Baseline: `78700e2be647f9fd88702566f4f9aee4df08503f`.
Branch: `integration/host-safety-notifications`; PR #2 Draft/unmerged.
Phase 0: 0/5 accepted. Main rules were reread for the source-research step.
Scope: static analysis of the three supplied libraries, documentation only.
No library loaded/executed, debugger, installation, project access, SDK publication,
product-code change, merge, deploy or release.

## Input and predeclared discriminator

The user supplied `FSTR-AE-Modules.zip` from the copy helper, not another partial
function report. Its SHA-256 matches the terminal output:
`2fb3acad42354fa7de409e1d8b14720cc6a4e546fbe5fad3cc5c38e3ec0fda7d`.
Exactly four entries were read: BEE.dylib, AfterFXLib, dvacore and manifest.json.
All module sizes/hashes match the manifest and the previous research baseline.
Original archive bytes are unchanged; extracted libraries are read-only and
are not being published to Git or uploaded to CI.

| Module | Bytes | SHA-256 |
| --- | ---: | --- |
| BEE.dylib | 31373056 | `817b9de9c6d57b5d6988b634842090e1528fe817a5685c8d1ff358553c6660ca` |
| AfterFXLib | 45998720 | `ce3aa2f16fe5449a77379a6b622e1a221596e511b86f7708dd3e2f7a3cced01a` |
| dvacore | 7772464 | `cb6faaf5b745903b80b44105b658ab68186d5065ae47c8a57c9b23e26aa8ecb0` |

The [previous decision](DIRECT-SUBSCRIPTION-FOCUS-2026-09-30.md) required rejecting
a dirty-only signal if it suppresses repeated dirty edits. We test that source
condition first, rather than implementing another collector or fixing LLDB.
These hashes establish received input identity, not the currently loaded Mac state.

## Dirty-state setter: reject as the standalone repeated-change source

All following addresses are unslid BEE arm64 addresses, not callable API handles.
`BEE_Project::SetContentChanged(bool)` at `0x3a1e10` compares the stored byte
`project+0x110` with the requested value at `0x3a1e2c`-`0x3a1e30`.
The equality branch at `0x3a1e34` jumps to `0x3a1ea0`, skipping the notification
block. Only the unequal path stores the new byte, checks signal slots at
`project+0x120`, binds `BroadcastDirtyState` and calls
`NotifySafelyOnUIThread` at `0x3a1e74`.

`BroadcastDirtyState` at `0x3a4b60` forwards project/bool arguments to that same
`+0x120` signal. `ConnectDirtyStateChangedSignal` also connects to `+0x120`
(at `0x3a6c34`-`0x3a6c44`). This ties the comparison to the proposed subscriber,
not merely to a similarly named flag.

For this setter with ordinary bool values and otherwise unchanged state:

| Previous | Requested | Enters notification block |
| --- | --- | --- |
| false | false | No |
| false | true | Yes; actual delivery still depends on later gates |
| true | false | Yes; actual delivery still depends on later gates |
| true | true | No |

Thus `false -> true -> true` has no second notification from this path. The
word `0x54000360` was independently decoded as B.eq to `0x3a1ea0`; the full
58-word setter body matches the corresponding mapped file bytes.

**Decision: reject this signal as the standalone source for every repeated
edit.** Do not reset AE's dirty flag to force events: that would change host
state rather than observe it. This is a static counterexample to relying on
the setter, not a runtime assertion that every second edit in AE is lost.
Other producers, intervening resets, UI gesture granularity and actual delivery
were not executed. A direct B/BL scan is not an exhaustive indirect call graph.

## Completion source: stronger discriminator, external subscription still open

The inspected `SetExecutingCommand`, `SetExecutingCommandGroup`,
`SetExecutingUndo` and `SetExecutingRedo` bodies select the completion signal
at `context+0xd8` when the observed execution flags transition from active to
inactive. Their decision reads execution flags `+0x66` through `+0x69`, not
the project dirty byte. `OnUndoCommandCompleted` at `0x649c6c` emits the same
signal when slots exist. Repeated operation boundaries can therefore reach
this emitter without requiring a clean-to-dirty project transition.

This is a reason to continue this candidate, NOT evidence that each required
Timeline action produces a callback, that delivery is post-commit, or that a
resident external AEGP can safely subscribe. Selection/playhead/context remain
separate coverage requirements. The earlier [native client record](COMPLETION-NATIVE-CLIENT-2026-09-29.md)
remains relevant; its render-queue transport is not adopted.

The exact Connect specialization below was absent from the arm64 export tries
of ALL THREE supplied modules, including the newly available dvacore:

```text
__ZN7dvacore9messaging6SignalIFvP15BEE_UndoContextELb1EE7ConnectENSt3__18functionIS4_EE
```

This is a scoped negative lookup, not a claim that no usable registration path
exists anywhere in AE. Do not cast a different Connect specialization or call
an internal address as a guessed workaround. `SetContentChangedCallback` is
also not an additive listener: the inspected body swaps the single callback
storage at `context+0x70`. Replacing the host's callback is not an approved route.

## Verification and reproduction

PASS: input ZIP/hash/entry checks, all three module hashes and identities;
ten complete BEE symbol bodies with 474 contiguous four-byte rows compared to
file bytes; independent equality-branch destination; three exact export-trie
lookups. The four boolean rows above are local branch evaluation, NOT four AE tests.
Compact identities/body ranges/hashes: [evidence JSON](evidence/direct-source-78700e2.json).

Tool: LLVM llvm-objdump 17.0.0 on Linux. Use separate option/value arguments:

```sh
llvm-objdump --macho --arch=arm64 --disassemble --dis-symname '__ZN11BEE_Project17SetContentChangedEb' BEE.dylib
llvm-objdump --macho --arch=arm64 --exports-trie AfterFXLib
```

Repeat symbol-specific disassembly for the names in the evidence JSON and
compare mapped raw bytes/body hashes. Source documentation:
https://llvm.org/docs/CommandGuide/llvm-objdump.html . An initial invocation
with `--dis-symname=...` was rejected by this tool; it produced no accepted
analysis. Corrected invocations all exited successfully. No new analyzer or
collector is added to the product/repository for this investigation.

Documentation consistency, evidence JSON parsing and whitespace checks apply.
Product build/runtime regression: N/A for this documentation-only increment
under rules section 9. Existing automated workflows are unchanged, and any
incidental CI outcome must remain distinct from static source evidence.
Real AE, native subscription and full SYNC-001: NOT RUN/BLOCKED. Issue #3 stays open.

## Next bounded step and SDK

Resolve an external completion-registration/context ownership path from the
received binaries and existing client evidence; do not resume general LLDB
maintenance as a prerequisite. Use a minimal disposable native proof only after
those contracts are known, with repeated edits, script origin and Undo/Redo.
A matching SDK is needed for compiling that AEGP proof; its archive is requested
in the conversation, not for publication in this public repository. Inspect its
version and terms before choosing any redistribution or CI storage policy.
No additional per-function report is requested from the user.
