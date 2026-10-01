# Real queue report review — 2026-09-30

Run: `QUEUE-REVIEW-t5rmrf54`. Baseline: `eef15f5803f69731acf825cd1d45b1ee7648e525`.
Phase 0; 0/5 phases accepted. Rules reviewed from main, blob
`701a8c1ae3acb4dbfe1d7eda94acbf8095b88608`. Scope: inspect the supplied offline
report, distinguish observations from hypotheses, and request the next observed
bodies. No private ABI invocation, installation, debugger attach or project access.

## Acceptance fixed before changes

Check ZIP members/CRC/SHA, exact kit/manifest/collector/policy linkage, required
body set, command results and observed-symbol provenance. Preserve historical
BLOCKED evidence. Review the relevant caller/callback/queue paths; do not infer
runtime thread or project ownership from a function name. For the small follow-up
launcher: bash syntax, unchanged-kit refusal before execution, exact argument and
exit-code forwarding, quoted paths, six pinned files and all 12 selected names.
Full branch build/regression is checked by exact-commit CI. Actual follow-up AE
collection is NOT RUN until its new report exists. No performance claim is made.

## Received evidence and identity

User-supplied archive: `report.zip`, run `FSTR-AE-Queue-t5rmrf54`.
Archive SHA-256: `95db0b6ff9bde57bb19bf3785d5d3dab7c02a910ef45cbeecdda44db213f75f7`.
`report.json` SHA-256: `bccf024bdef4fcb11d036ae6b1aeeb7b5a84f6b3ee1324f3cb89b1f4cca81e01`.
Both ZIP members (`report.json`, `SHA256.txt`) read successfully; the sidecar matches.
Build ID: `fstr-queue-eef15f5803f6`; source state: clean, source commit: baseline.

The manifest and five payload hashes match the previously delivered unchanged
Queue ZIP, SHA-256 `e39612905f239cb0dc755053a63ea34cb88aa48762913065912a33741e02353c`.
Report-declared module identities match its exact AE 25.6.0.101 arm64 policy:
BEE `817b9de9c6d57b5d6988b634842090e1528fe817a5685c8d1ff358553c6660ca`,
AfterFXLib `ce3aa2f16fe5449a77379a6b622e1a221596e511b86f7708dd3e2f7a3cced01a`.
This is verification of supplied evidence, not an independent live Mac rehash.
The collector reports 14 successful bounded commands, seven unique required
bodies (1,399 instruction rows) and 47 inventory entries. BEE has 19 ambiguous
names and AfterFXLib 137; none of the required names is ambiguous. Thus the new
report demonstrates successful collection on the previously blocked modules.
It does not retroactively change the old BLOCKED report.

The compact provenance and exact next symbols are in
[evidence/queue-eef15f5-review.json](evidence/queue-eef15f5-review.json).
Full Adobe disassembly and user filesystem paths are not copied into Git.
Original nm streams are not in the report: their hashes cannot recreate them or
prove global absence of another exported registrar.

## Findings from the received bodies

All addresses are unslid and specific to these reported module hashes. This
review covers the named paths below, not every path in the 1,030-row caller.

| Path | Evidence and bounded conclusion |
| --- | --- |
| BEE `0x7913dc`–`0x7913f0` | The exported posting wrapper returns normally without posting when its queue pointer is null. Otherwise it tail-branches to PostGenericFunction. |
| BEE `0x780f38`–`0x780f70` | The generic posting call sets x2 to zero before AddFunctionToQueue at `0x780f50` (the named UndoContext argument); nonzero w0 conditionally invokes another stored callback. Neither a commit acknowledgement nor FIFO semantics follows from this body. |
| BEE `0x781040`–`0x781074` | Execution obtains GetProjectClone, passes that pointer into ProjectSetContext and the queued callback, then destroys the context guard. The same guard cleanup appears on unwind paths. |
| BEE `0x3699f0` | GetProjectClone is a load from the supplied globals object's `+0x18`. It does not return a documented AEGP handle or acquire visible shared ownership in this body. |
| AfterFXLib `0x885d98`–`0x885ea4` | The native effect obtains its project/UndoContext through internal layer objects. Activity selects a temporary completion subscription; the inactive branch posts directly at `0x885f0c`. |
| AfterFXLib `0x8869e0` and inventory | The exact completion Connect specialization is defined only in full nm, not exported-defined nm. Presence of other exported accessors is not an external registration/ownership contract. |
| AfterFXLib `0x89c2d8`–`0x89c350` | The callback posts, then calls Disconnect at `0x89c308`. Its exceptional unwind path does not execute that normal-path Disconnect. |

**New composed failure-path inference:** if this callback runs while the global
queue pointer is null, the posting wrapper returns without queuing the work and
the callback still reaches its normal Disconnect. Consequently “post returned”
cannot be a success acknowledgement. This is a conditional path inferred from
two received bodies, not an observed real-AE dropped notification. Queue absence
at that time, actual ordering and recovery require separate evidence.

**Project/thread decision:** the execution-time clone is not evidence of the
registration-time UI project's identity/freshness. Do not use this path for a
public AEGP snapshot or claim it is main-thread dispatch. The newly observed
`ProcessFromRenderThread` is a concrete next inspection target, not proof based
on its name that every generic function executes on that thread.

## Undecoded text is not silently accepted as full analysis

The two AfterFXLib bodies contain 20 `.long` rows (nine distinct words). The old
collector's PASS checks body presence/contiguity; it does not reject this form.
Therefore this report is not a full instruction-decoding/CFG PASS.

The nine supplied words were assembled verbatim into a test-owned arm64 Mach-O
object and disassembled with local LLVM 17 and `--mattr=+lse`. They decode as:

```text
f8290108 -> ldadd   x9, x8, [x8]
f8280328 -> ldadd   x8, x8, [x25]
f8e90108 -> ldaddal x9, x8, [x8]
b8290108 -> ldadd   w9, w8, [x8]
b82a012a -> ldadd   w10, w10, [x9]
b8e80128 -> ldaddal w8, w8, [x9]
b8e90108 -> ldaddal w9, w8, [x8]
f8280308 -> ldadd   x8, x8, [x24]
f8e80308 -> ldaddal x8, x8, [x24]
```

This decodes supplied instruction words; it does not execute Adobe code, establish
its C++ ABI, prove thread safety or test the user's Apple LLVM with another flag.
The original report is unchanged. Tool option reference:
https://llvm.org/docs/CommandGuide/llvm-objdump.html (`--mattr`).
The queue/clone call-site conclusions above do not depend on these raw rows.

## One bounded next request, no new collector build

`research/ae-notifications/Queue-Inspect-Observed.command` reuses the unchanged
six-file eef15f5 kit, checking all six hashes before running its launcher. Its
default path is the project-local kit directory supplied in the user's terminal
output, under HOME; it never searches the disk. An explicit kit directory and
optional `--verify-only` are supported. No files are installed or overwritten.

All 12 names are copied from this report's unique BEE inventory entries:
AddFunctionToQueue, ProcessFromRenderThread, Render_DeserializeFullProject,
ProjectBirth/ProjectDeath, GetProject/GetProjectFaux,
IsProjectOpen/IsProjectCloneOpen, GetUndoContext, RegisterListener/DeregisterListener.
The existing seven roots and collector refusal checks remain. The follow-up
requests bodies, not calls; it has no offsets or guessed function prototypes.

Acceptance of the next report requires all 19 bodies with fresh identity checks.
Then inspect enqueue/dequeue and serialization order, clone birth/replacement/
death, and actual listener contracts. These functions may expose further unknowns;
this request is not a promise that twelve bodies close the production gate.

## Executed verification and limits

Local Linux: six new launcher contract tests PASS; bash syntax PASS; the exact
old eef15f5 kit passes real shasum verification and its real `--verify-only` path
through the new launcher. Argument-forwarding controls use a clearly fake owned
launcher and fake hashing success; they do not prove AE collection. Real refusal
controls use actual shasum and confirm that invalid payload is not executed.
The supplied report's full body set also passes the unchanged collector parser.

Local full checkout/build was unavailable (GitHub DNS failed). Exact-commit
Linux/macOS CI results are recorded separately in PR #2; earlier checks do not
cover this commit. No retries-to-green, relaxed checks or deadline changes.
Main/merge/deploy/release and user projects are unchanged. Issue #3 remains open.

SYNC-001, queue runtime order/thread, UI-clone association, safe external context/
registration, callback quiescence, source coverage and uninstrumented performance
remain NOT RUN/UNPROVEN. Only the report review and follow-up request are complete.
