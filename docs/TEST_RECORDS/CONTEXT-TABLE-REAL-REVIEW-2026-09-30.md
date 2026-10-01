# Context helpers and resolved command table — 2026-09-30

Run: `CONTEXT-REVIEW-2mniyqyl`. Baseline:
`af0b8b9f2b4629f3dfc2b5bfca01f57e2ec21438`. Phase 0; 0/5 accepted.
Main rules reviewed: blob `701a8c1ae3acb4dbfe1d7eda94acbf8095b88608`.
Scope: review supplied offline evidence and prepare one pinned next body request.
No Adobe invocation/attach, SDK ABI adoption, project access or product change.

## Acceptance fixed before implementation

Verify archive members/CRC/sidecar, delivered kit/manifest/collector/policy linkage,
both module identities, all five requested bodies and successful bounded commands.
Reparse bodies with the unchanged collector; independently recompute table targets.
Separate directly observed instructions, composed conditional paths and unproven
runtime claims. Preserve original reports and prior FAIL/UNPROVEN history.

The next profile must request only eight unique names present in this report,
not guess names or follow arbitrary jumps. Both module identities and all names
must pass before any disassembly. Missing/ambiguous/incomplete/changed inputs
must not produce PASS. Existing profiles, budgets and private-call prohibition
remain. Required checks: local selection/refusal/package tests, actual Apple-linked
positive control and exact-ZIP launcher/refusal/collection checks in macOS CI,
full exact-commit branch gates before a handoff. No retry-to-green or waived gate.

## Received report and verification

Received `FSTR-AE-Queue-2mniyqyl`, `collectionStatus=PASS`,
Build ID `fstr-queue-af0b8b9f2b46`, clean source at the baseline above.

- ZIP SHA-256: `01f05cb593648ba6fd60d044f4c765af0d21bf0a79729340deb41c5d66448d3a`.
- report.json: `29e9da5007a37e6f2cf74969dd61e29383e5ada2ef6eaa452d664fdb9fa5b6f4`.
- Delivered kit ZIP: `fcf7557bf7f0b766c11c35bc3090971964f268c00e9489e9dd7f16fe11c683d1`.
- Manifest: `91285b49a701bdd021ba3b1e8c1e87a0ebd5dfbd816595e1c060bc5c7b30ec45`.

Both ZIP members read with valid CRC; sidecar matches. All seven kit payload
hashes, collector/policy hashes, source and Build ID match the delivered package.
The supplied SHA-256/arm64 UUID values match the exact AE 25.6.0.101 policy for
BEE and AfterFXLib. This is consistency verification of supplied evidence, not
an independent live-Mac rehash. All 12 recorded commands completed successfully.
All five bodies reparse at their unique inventory addresses: 746 contiguous
four-byte rows (12, 13, 1, 1, 719). Apple LLVM reported version 21.0.0.

Compact identity, per-body redacted-text hashes, full 19-entry BEE inventory and
table are retained in [evidence/context-af0b8b9-review.json](evidence/context-af0b8b9-review.json).
Full Adobe disassembly and user filesystem paths are not published into Git.
Raw nm streams are not included in the supplied report; their hashes cannot
prove absence of a registrar across all modules.

## 1. CommandType 0 is now mapped to the load/drop arm

The four bytes at BEE unslid `0xe8c4d4` are `00 29 2b 2f`.
File offset `0xe904d4`, arm64 slice offset `0x4000`, `__TEXT,__const`.
Bytes SHA-256: `abe02b6e22150486a00dac6568cc79fbcbaf030f4a52efa79aaa3967f44b4307`.

At `0x777c7c`, ADR selects `0x777c8c`; LDRB loads an unsigned table byte,
and `0x777c84` scales it by four before BR. Independent arithmetic gives:

| Numeric CommandType | Destination | Bounded static observation |
| --- | --- | --- |
| 0 | `0x777c8c` | Test queue member `+0xa8`; zero goes to timestamp/enqueue, nonzero enters the shown load/drop path. |
| 1 | `0x777d30` | Clear the same member, then enter timestamp/enqueue. |
| 2 | `0x777d38` | Set member to one and use timestamp value zero before enqueue. |
| 3 | `0x777d48` | Test/clear member, then enter timestamp/enqueue. |

These are numeric arms and observed storage uses, NOT adopted enum declarations.
The prior [queue review](QUEUE-ORDER-CLONE-2026-09-30.md) established that the
generic poster supplies numeric type 0; the missing table prevented mapping it.
The new table closes precisely that static ambiguity.

With `queue+0xa8 != 0`, the type-0 path calls the current-context helper and
load/run-mode checks, may report an illegal sequence, then takes debug trace
branches to `0x778478`. At `0x778258` the diagnostic names a drop during load;
`0x778478` zeros return-path state and rejoins cleanup without the command
allocation/back-insertion at `0x777d74`–`0x777ec8`. With the member zero, the
branch instead reaches timestamp/enqueue at `0x777d58`.

**Composed conditional conclusion:** this generic posting path is not immune
to pre-enqueue rejection during the internal state diagnosed as loading. The
statement assumes the shown helper calls return normally; it is not a runtime
loss count, proof that FSTR has lost an event, or proof of when `+0xa8` changes
in the user's workflow. No callback acknowledgement/recovery contract follows.
Earlier records correctly left the table unknown and are not rewritten.

## 2. Global project query is not the current-context query

`BEE_QueryProject`, `0x65ef40`–`0x65ef6c`, passes globals at `0x11aedf0` to
`BEE_Globals::GetProject`, writes the returned pointer through its input at
`0x65ef5c`, and returns numeric zero at `0x65ef60`. No result-null test, ownership
acquisition or lifetime validation is visible in this body. A zero return cannot
be used alone to prove a usable project. No null call was attempted.

`BEE_GetCurrentConstProject`, `0x65efa4`–`0x65efd4`, instead calls the imported
`TDB_GetCurrentConstProject`, returns a null result directly, or tail-calls
`__dynamic_cast` with the returned pointer. The TDB body and typeinfo objects
are not supplied. Do not infer TLS layout, ownership, casting guarantees,
main-thread permission or UI-project association from the helper's name.

Combined with the prior clone accessor evidence, these are distinct access paths,
not interchangeable public AEGP project handles. This report does not prove which
project the current context denotes on a particular thread.

## 3. Two requested entrypoints are only forwarding branches

`BEE_ProjectSetContextC1EP11BEE_Project` at `0x39f8e0` consists only of a branch
to the observed C2 symbol (inventory address `0x39f57c`). D1 at `0x39fc08` consists
only of a branch to D2 (inventory address `0x39fa54`). The one-row bodies are
complete as collected, but do not expose construction/destruction behavior.
No destructor, lock, restore or exception-safety contract is inferred from them.

The next request uses the exact C2/D2 names, two context accessors, default C2,
queue C2/D2 and the observed speculative-preview state-change function. Every
name is unique in the supplied inventory. That last function is a bounded lead,
not a claimed emitter for RegisterListener. Further callsites may still be needed.

## 4. Raw instruction rows and verification limits

The anchor body contains five `.long` rows, three distinct supplied words.
A test-owned arm64 Mach-O object containing exactly those words was assembled
with local clang and decoded with LLVM 17 `--mattr=+lse`:
`b8290108` -> `ldadd w9,w8,[x8]`; `b8e08108` -> `swpal w0,w8,[x8]`;
`b8e90108` -> `ldaddal w9,w8,[x8]`. This does not execute Adobe code or prove ABI
safety. The original file is unchanged; collection PASS is not full CFG acceptance.

## Next request implementation and executed controls

`Queue-Details.command` selects `context-details`. It uses the existing collector
and fixed eight-name request, without a table/range read or old root-body reread.
Both modules are verified; the inventory covers bounded top-level WorkQueue and
queue/context method names. No arbitrary address/module or recursive branch
following is introduced. Extra selections and mixed profiles are rejected.

Local: 12 new tests, **11 PASS / 1 NOT RUN** (real Apple-linked control requires
macOS). Included provenance, full set, missing/ambiguous functions, partial tool
failure, wrong address, persistent replacement, both-module identity, bounded
inventory, unchanged roots, conflicting CLI flags, clean owned-Git packaging,
executable modes, Unicode/spaced paths, verify-only and refusal before writes
inside an app or after payload corruption. Bash syntax and Python AST checks PASS.
Local sources are a blob/hash-verified subset; clone failed DNS. Full repository
build/regression and real Apple-tool results belong to the exact containing
commit's CI/PR record, not the local subset or earlier SHA. No performance claim.

The original SYNC-001 claims stay UNPROVEN/NOT RUN. Shipping registration,
callback lifetime/quiescence, active UI association, post-commit coverage and
uninstrumented performance remain unaccepted. Issue #3 remains open. Neither
this review nor the future offline report constitutes a production notification
mechanism. Main, user projects, merge/deploy/release remain untouched.
