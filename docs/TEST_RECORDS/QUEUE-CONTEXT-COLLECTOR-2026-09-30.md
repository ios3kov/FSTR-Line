# Queue/context evidence collection — 2026-09-30

Run ID: `QUEUE-STATIC-20260930-01`.
Baseline: `9393e3c722dff6a74dba2fcd5fc73b831c682ffd`.
Branch: `integration/host-safety-notifications`; PR #2 remains Draft/unmerged.
Rules reread from main commit `c69e3663de59dc44cbdef18042891f6dd1ce5ee6`,
`DEVELOPMENT_RULES.md` blob `701a8c1ae3acb4dbfe1d7eda94acbf8095b88608`.
Phase accounting: 0 of 5 phases completed. SYNC-001 is still BLOCKED/NOT RUN.

## Scope and acceptance

Prepare a reproducible, read-only next step for queue ordering/thread, clone
association and external registration/context research. Do not execute private
Adobe functions, subscribe, attach, install, change the CEP package or touch a
user project. This is a research-tool increment, not shipping delivery.

Required checks: identity rejection before inspection; positive evidence for
every requested body; bounded tool execution/output; controlled failure paths;
owned Mach-O control; tests and syntax; full existing branch CI. Render output,
bit-depth and runtime performance comparisons are N/A for this collector-only
change; they remain mandatory where applicable to the future native product.

The existing deep-static collector checks tool exit codes but does not validate
each requested body. The new queue-specific path must not interpret a zero exit
with empty/wrong disassembly as complete evidence. The older collector is not
modified by this increment.

## Implementation

`research/ae-notifications/queue_static.py` uses the existing `deep_targets.json`
identity policy for AE 25.6.0.101, BEE and AfterFXLib. It verifies both module
hashes and the specifically selected arm64 UUID before nm or disassembly.
A universal binary's first UUID is not automatically its arm64 UUID.

Seven literal roots come from the earlier
[completion client record](COMPLETION-NATIVE-CLIENT-2026-09-29.md): the two
posting functions, Render_GenericFunction, GetProjectClone, SamuraiUpdateParamsUI,
the completion Connect specialization and its native callback. No prototype,
address-based call, closure layout or subscriber is synthesized.

For each module, full-defined and external-defined nm tables produce a bounded
inventory of queue, project/clone, thread and registration leads. These are
**nm visibility observations**, not a dlsym/export-trie or callable-ABI guarantee.
A missing symbol is only missing from that particular completed module scan.
It never proves absence in other modules or through indirect registration.

Every requested body must have its exact label, match its nm start address and
contain contiguous decoded arm64 instructions. Missing/ambiguous/wrong bodies,
failed tools and incomplete output block collection. Saved branch sites are
static leads, not observed execution order. A complete body capture does not
prove a full control-flow graph, callback success or post-commit semantics.

Output is bounded while each child runs (not after unbounded capture): 60 seconds
per tool, 64 MiB per nm invocation, 2 MiB per body/version/UUID command, at most
256 inventory names per module, at most 2 GiB per input binary. Only the newly
created tool process group is stopped on timeout/overflow. No user/AE PID is
accepted or inspected. Module paths must resolve inside the selected app; hashes
and resolved paths are checked again at the end to catch persistent replacement.
This is not a defense against an adversarial replace-and-restore race.

Each report gets a fresh directory, Run ID, collector SHA-256, policy SHA-256
when read, timestamp and a SHA-256 sidecar. Existing reports are not overwritten.
Application/home paths, including Unicode and quotes, are redacted before JSON encoding. `collectionStatus: PASS` means collection
checks passed, not AE acceptance: all semantic claims remain UNPROVEN,
`privateInvocationAllowed` is always false, and `SYNC-001` remains NOT RUN.
The CLI refuses non-macOS without invoking host inspection tools.

## Research clarification, not a new runtime result

The Adobe-authored SDK guide describes AEGPs as resident for the AE session and
requires their ordinary API work to run on the main thread in host callbacks.
A future resident AEGP component could therefore separate native callback-code
lifetime from CEP panel reload. This is a candidate architecture, not approval
of any private registration path: owner lifetime, closed generations, in-flight
callbacks and shutdown still need independent proof.

The SDK history also describes UI/render project copies and serialization of
changes between them. This supports treating clone identity/freshness as a real
obligation, not assuming that a queued callback sees the current UI project.
It does **not** identify the runtime role of the two observed context addresses
or prove how the exact AE 25.6 queue orders updates.

Primary sources checked 2026-09-30:
- [Adobe SDK guide: AEGP implementation, Private Data and Threading](https://ae-plugins.docsforadobe.dev/aegps/implementation/).
- [Adobe SDK guide: project copies and UI/render synchronization history](https://ae-plugins.docsforadobe.dev/intro/whats-new/).
- [LLVM objdump: Mach-O-specific --arch and --dis-symname](https://llvm.org/docs/CommandGuide/llvm-objdump.html).

No new licensed Adobe binary evidence was available in this session. Earlier
[ABI](NATIVE-SUBSCRIPTION-ABI-2026-09-29.md),
[lifetime](NATIVE-SUBSCRIPTION-LIFETIME-2026-09-29.md) and
[UI ordering](UI-DISPATCH-ORDER-2026-09-29.md) records remain unchanged.

## Verification

Local environment: Linux x86_64, Python 3; source subset prepared from the
connector. Terminal Git network access was unavailable, so the full repository
build/regression is delegated to exact-commit GitHub Actions, not claimed locally.

| Check | Result and scope |
| --- | --- |
| New unittest discovery | 22 tests: 21 PASS, 1 Apple-tools control NOT RUN/skipped locally |
| Real owned arm64 Mach-O object | PASS: clang cross-compilation plus actual llvm-objdump, no Adobe code |
| Synthetic collection and refusal matrix | PASS: build/hash/UUID/architecture, missing/wrong bodies, tables, path escape, replacement, limits |
| Real owned subprocess controls | PASS: success, nonzero exit, invalid UTF-8, output overflow, deadline including a closed stdout pipe |
| Unique report and SHA-256 | PASS; repeated output cannot reuse an earlier report |
| Non-macOS CLI | BLOCKED as required, exit 2, MACOS_REQUIRED; no host inspection |
| Actual Apple tools | Separate owned-dylib test automatically runs on macOS CI; not a local PASS |
| Full branch tests/build/package | Results belong to the exact containing commit's GitHub Actions checks; no earlier SHA's result is substituted |
| Real licensed AE collection/runtime | BLOCKED here: no exact Adobe modules or AE process in this environment |
| Shipping source, queue thread/order, clone mapping, ABI and delivery | NOT RUN/UNPROVEN |

During this increment, the first real LLVM object control exposed rejection of
compact instruction addresses (`0:` / `4:`). The parser was corrected and that
exact format gained a regression test before committing. This was an internal
collector defect, not evidence of a fixed AE runtime issue. An attempted local
Mach-O dylib link was unsupported by this container's linker; the local positive
control uses an object file. macOS CI separately builds an owned dylib.

Reproduce local controls:

```sh
python3 -B -m unittest discover -s tests/research -p test_queue_static.py -v
```

Research-only collection on an authorized Mac, without launching/attaching AE:

```sh
python3 -B research/ae-notifications/queue_static.py \
  --app "$EXACT_LICENSED_AE_APP" --output "$OWNED_RESEARCH_OUTPUT"
```

The existing Integration gate discovers the tests; mac-research also discovers
them. CI logs/check-runs are external exact-commit evidence, avoiding a recursive
source change merely to insert the tested commit's own SHA into this record.
No installable artifact is handed to the user by this change.

## Next bounded work and stop conditions

1. Collect the pinned modules and inspect the discovered AddFunctionToQueue,
   worker/dispatch and serialization/deserialization paths. Establish which
   completion acknowledges which update; names and FIFO assumptions are not proof.
2. Correlate clone/UI project identity and generation across queued work,
   project switch, reopen and pending cancellation using independent state.
   Old-project work must not publish as the new project's current state.
3. Locate and validate an external context acquisition and registration path,
   including return/callback ABI and owner/shutdown lifetime. An opaque public
   project handle must not be cast to an inferred private pointer.
4. Only after these contracts are evidenced, use a disposable native harness;
   subsequently verify the full actual-source change matrix and uninstrumented
   performance. No periodic/idle/focus/self-event substitute is introduced.

Missing identity, truncated tools, missing required bodies or unknown contracts
stop the corresponding step as BLOCKED. LLDB remains research only. Main,
production, preferences, security settings and user projects remain untouched.
