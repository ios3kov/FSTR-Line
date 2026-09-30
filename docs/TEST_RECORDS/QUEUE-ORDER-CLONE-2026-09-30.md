# Queue order, clone lifecycle and context boundary — 2026-09-30

Run: `QUEUE-ORDER-qk6xsvhj`. Repository baseline:
`c8431386d2dc123e85f6c0c78cee621e31037f83`.
Phase 0; 0/5 phases accepted. Main rules blob remains
`701a8c1ae3acb4dbfe1d7eda94acbf8095b88608`.
Scope: review the supplied 19-body offline report, not call private Adobe code.
This increment changes documentation only. No collector rebuild, installation,
debugger attach, project operation, merge, deployment or release.

## Acceptance and evidence identity

Checks for this stage: archive members/CRC/SHA; delivered-kit, manifest,
collector and policy linkage; all seven roots plus the twelve exact requested
names; command success, unique body addresses and row contiguity; explicit
handling of undecoded words; conclusions bounded to observed instructions.
Document consistency/whitespace and exact-commit CI are separate from AE runtime.

The current upload is the requested new report, not the earlier seven-body ZIP:

| Item | Verified value |
| --- | --- |
| Run ID | `FSTR-AE-Queue-qk6xsvhj` |
| Archive SHA-256 | `df6a451e11c3a02160fc1d89d75a45653c46f6380208f1b454767fabff9d2123` |
| report.json SHA-256 | `f41cd06d1fd1bca74f0dc0d4085ebe1ba89dc909bea6f81ba2cec730057ae335` |
| Source commit | `eef15f5803f69731acf825cd1d45b1ee7648e525` |
| Build ID | `fstr-queue-eef15f5803f6` |
| Original Queue ZIP SHA-256 | `e39612905f239cb0dc755053a63ea34cb88aa48762913065912a33741e02353c` |
| Manifest SHA-256 | `53d1177b74ea98e45fe5d12c574fc2a70ec230a277910dc52867fd047f650258` |
| Collector SHA-256 | `3dafe1c99a4a7aebf9f235e6f6c8341e60c6e2a3d0b85aa46dfea0f6122403bb` |
| Policy SHA-256 | `1e748db1d0c565f02e23133f265b3d5768445dddabbddcf40c23114c5dee96f5` |

Both ZIP members (`report.json`, `SHA256.txt`) were read and the sidecar matched.
The supplied report matches the delivered immutable kit and the twelve selections
in `Queue-Inspect-Observed.command`. All 26 command records report successful,
complete output. All 19 requested bodies are present at unique inventory addresses:
16 BEE and 3 AfterFXLib bodies, 5,029 contiguous four-byte instruction slots.
There are 47 inventory entries. No new collection is needed to review this input.

Reported AE: 25.6.0.101 arm64; collection tool: Apple LLVM 21.0.0.
Reported BEE SHA-256:
`817b9de9c6d57b5d6988b634842090e1528fe817a5685c8d1ff358553c6660ca`,
UUID `161300f3-73f8-3ebc-a751-959df40a073b`.
Reported AfterFXLib SHA-256:
`ce3aa2f16fe5449a77379a6b622e1a221596e511b86f7708dd3e2f7a3cced01a`,
UUID `edc800d6-9e4b-3a03-9bbb-8239f3f6eea5`.
These match the pinned policy; this is supplied-evidence verification, not an
independent rehash of the user's Mac or proof of a loaded process's identity.
The original upload and earlier reports remain unchanged. Full Adobe disassembly
and user filesystem paths are not copied into Git.

## New bounded static findings

All addresses below are unslid BEE addresses for the reported binary. Member
roles are descriptions of their observed use, not supported C++ declarations.

### 1. Ordered removal is not a delivery/completion guarantee

`AddFunctionToQueue` queries a project at `0x777c54`, then acquires the queue
mutex at `0x777c64`. Its insertion path increments `queue+0xa0` at
`0x777d68`–`0x777d70`, supplies that value to `QueuedCommand` construction, and
appends shared command storage at the deque's back (`0x777e50`–`0x777ec8`).

`ProcessFromRenderThread` locks its queue-object mutex at `0x781788`, copies
the front entry (`0x7817b8`–`0x7817e8`), advances the front index and reduces
size (`0x781854`–`0x781860`), then unlocks at `0x7818ac`. Only afterwards does
it invoke the stored function at `0x7819f0`.

This establishes back-insertion/front-removal on these paths. It does not prove
single-consumer execution, globally ordered callback completion, or UI dispatch.
The lock is not held across the callback. Caller-side serialization and actual
thread identity are outside this report; the function's name is not runtime proof.

The batch compares `queue+0xb0` with the requested value at
`0x78176c`–`0x781774`; on the normal completion path it copies `command+0x28`
into `queue+0xb0` at `0x7825a8`–`0x7825ac`. Its final comparison/return is at
`0x782ce4`–`0x782cec` and `0x782fa8`. These observed watermarks are not a
per-command success receipt or a proven committed-UI-state oracle.

### 2. Cancellation and error paths defeat a lossless-queue assumption

At `0x78178c`–`0x7817a4`, a nonzero cancellation check clears the pending deque
before reading its next entry. The function also contains a catch/cleanup path
at `0x782878`–`0x782a48` that returns to command cleanup and the loop, rather
than providing a per-item acknowledgement to the external poster.

The current item has already been removed before invocation. Thus copying a
callback into this queue is not sufficient evidence of reliable delivery.
The report does not contain exception tables establishing every throwing
callsite's handler, nor does it show an actual lost event, callback exception,
retry, or recovery in AE. No blanket exception-coverage claim is made.

An additional load-time drop path exists in AddFunctionToQueue, with the
`DROP due to delta during load` diagnostic and false-return path at
`0x778478`–`0x778490`. However the CommandType dispatch uses an absent four-byte
jump table at `0xe8c4d4` (`0x777c68`–`0x777c88`). The generic poster passes
CommandType value 0, but this report cannot map that value to a switch arm.
Do not claim that generic callbacks take the load-drop arm without those bytes.

### 3. The clone is separate storage, not an owned UI-project handle

`ProjectBirth` invokes `BEE_Project::Create` three times with numeric kind values
1, 3 and 2 at `0x3690d0`, `0x36914c`, `0x3691c8`, storing each returned
16-byte ownership pair into globals offsets `+0x8`, `+0x18`, `+0x28`.
The GetProject/GetProjectClone/GetProjectFaux accessors load the corresponding
object pointers. This identifies distinct allocation paths and storage roles;
no undocumented enum declarations or constructor ABI are adopted.

`ProjectDeath` clears/releases the three ownership pairs at
`0x369720`–`0x36979c`. Its shutdown diagnostic is not evidence that this function
runs on every user project close/open. Logical project identity across file
switches, object reuse and application lifecycle remains a separate question.
The raw getters do not visibly acquire caller ownership or validate a lifetime.

`Render_DeserializeFullProject` obtains the clone at `0x7837d0`, passes that
same pointer to the XML deserializer at `0x7837ec`, then calls
`Render_AfterFullProject` at `0x7837fc`. Along with execution-time clone selection
in Render_GenericFunction, this is evidence of a separate replicated project
path, not a public main-thread snapshot dispatcher. Freshness and the complete
association with the active UI project are not established by these bodies.

### 4. Project-ID checking here is after execution

After calling the queued function at `0x7819f0`, the processor compares the
command's nonzero 16-byte identifier with the clone's identifier at
`0x781cac`–`0x781cd0`. The shown mismatch branch diagnoses and rejoins processing;
it does not prevent the already completed invocation. An all-zero identifier
skips that comparison.

This check cannot serve as FSTR's pre-call project-context guard. The statement
is limited to this processor; other native callbacks may have their own guards.
No wrong-project mutation was attempted or observed.

### 5. Accessor/export discovery has not solved external registration

`BEE_Project::GetUndoContext` (`0x3a9b80`–`0x3a9b88`) loads a member at `+0x318`
and returns an interior pointer at `+0x10`, without visible null/lifetime checks.
Together with the raw project getters, this is not a lifetime-safe external
context-acquisition contract.

RegisterListener (`0x7eaa3c`) creates a GUID and stores a copied Boost callback
in a global map under a shared/upgrade lock. DeregisterListener (`0x7eac80`)
locks that map and erases by GUID. The map at `0x11a52a0` and lock at
`0x11a52f8` are not the threaded-update queue pointer at `0x11a46f8`.
No emitter or association between these two structures is supplied here.
Do not combine similarly named WorkQueue APIs into a notification channel by
assumption. Erase alone does not establish callback quiescence or unload safety.
The exact Undo-completion Connect specialization remains non-exported in the
scanned AfterFXLib table; no global absence claim follows for other modules.

## Undecoded words and reproducibility

The original report contains 50 `.long` rows, representing 12 distinct words.
All were decoded locally using an owned AArch64 object and LLVM 17.0.0 with
`--mattr=+lse,+rcpc`. The words were assembled verbatim using `.inst` and were
never executed. Word identity and the count were checked against the input:

```text
38bfc108 ldaprb w8,[x8]       b8290108 ldadd w9,w8,[x8]
b82a012a ldadd w10,w10,[x9]   b8e08108 swpal w0,w8,[x8]
b8e80128 ldaddal w8,w8,[x9]   b8e90108 ldaddal w9,w8,[x8]
f8280308 ldadd x8,x8,[x24]   f8280328 ldadd x8,x8,[x25]
f8290108 ldadd x9,x8,[x8]    f8bfc108 ldapr x8,[x8]
f8e80308 ldaddal x8,x8,[x24] f8e90108 ldaddal x9,x8,[x8]
```

Reproduction: write the distinct hex words from the report as `.inst WORD`
rows under `.text`, compile with `clang++ -target aarch64-linux-gnu -c`, and
inspect that owned object using `llvm-objdump -d --mattr=+lse,+rcpc`.
Tool reference, consulted 2026-09-30:
https://llvm.org/docs/CommandGuide/llvm-objdump.html .
Decoding these words does not recover missing jump tables, exception tables,
indirect call targets or a complete control-flow graph.

## Verification, decision and next bounded work

PASS: supplied ZIP/CRC/sidecar; kit/source/policy identity; exact 19-body request;
26 successful command records; 5,029 contiguous instruction slots; local decoding
of all 50 raw-word rows. PASS is confined to evidence integrity/static review.
Documentation checks apply under rules section 9. Full branch CI, when completed,
is recorded for this increment's exact commit in PR #2, not borrowed from c843138.

NOT RUN: Adobe execution, live thread tracing, private ABI invocation, actual
notification delivery and performance. Full local branch build is BLOCKED by
GitHub DNS in this Linux container; no build result is inferred from that fact.
No installable product artifact is handed off by this documentation-only stage.

Decision: do not select BEE_WorkQueue_PostGenericFunction as a standalone,
lossless, committed-UI notification transport. It may participate in a future
proven composition, but these queue and context limitations need explicit
solutions, not polling, guessed layouts, copied addresses or debugger hooks.
The 19-body static-review substep is complete; Phase 0 and SYNC-001 are not.

Next inspect the actual caller/binding of the callback at queue offset `+0x40`
to establish the scheduling thread, and the already observed call targets
BEE_QueryProject, BEE_GetCurrentConstProject and BEE_ProjectSetContext for
context selection/ownership. Recover the four CommandType jump-table bytes
before assigning drop behavior to value 0. Separately identify the WorkQueue
listener emitter and its relationship, if any, to project-update commands.
These are missing contracts, not permission to invoke private functions.
Do not ask for another identical 19-body run. Further collection must target
these specific gaps and preserve the already verified kit and user environment.
Issue #3 (research LLDB shutdown timeout) remains open and is not fixed by this
static review. No source or runtime acceptance requirement is relaxed.
