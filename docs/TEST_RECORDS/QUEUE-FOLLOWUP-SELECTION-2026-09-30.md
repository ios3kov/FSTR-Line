# Queue/context follow-up selection — 2026-09-30

Run ID: `QUEUE-FOLLOWUP-20260930-01`.
Baseline: `d497393ed2617b1c2721b3118618812c52f25071`.
Phase: 0 of five phases (0–4), no phase acceptance closed.
Rules: current main blob `701a8c1ae3acb4dbfe1d7eda94acbf8095b88608`,
sections 1–4, 6–12, 14–16, 20–22, 24 and 27.
Scope: read-only research tooling, not a CEP/native production change.

## Goal and acceptance

The preceding collector disassembles seven known roots, but only inventories
additional queue/context functions. Following an actual queue consumer, clone
lifecycle or context-acquisition lead required an unrecorded manual command.
Add bounded selection from that same research scope, with fresh identity and
symbol checks. Do not infer callable ABI or install any subscriber.

Required checks: unchanged default root coverage; positive selection from both
modules; exact limit and duplicate refusal; bad input refusal before host reads;
all-module identity and symbol preflight before disassembly; no partial PASS
when a requested body fails; existing replacement/timeout/output/path guards;
CLI/report/hash identity; original queue tests; exact-commit integration and
macOS research CI. A real Apple-tools end-to-end control is required on macOS.
Actual AE queue/thread/clone/registration evidence remains a separate gate.
No tolerance is allowed for silently skipped requested bodies.

## Implementation

`queue_static.py` accepts repeated `--inspect-symbol MODULE:SYMBOL` arguments.
Only `BEE` and `AfterFXLib` from the pinned policy are allowed. Each name must be
an exact simple Mach-O symbol in the existing queue/context research scope,
and present in the current arm64 text-symbol table. Requests do not import a
policy, accept an address, create a shell command, or authorize native calls.
A new matching name is a discovery lead, not an ABI declaration.

At most 12 explicit requests are accepted; an already-required root is read
once. Duplicate requests, comma-separated names, whitespace/control characters,
unknown modules, addresses and out-of-scope names refuse collection. A stale
name from an earlier report must still exist in this run's verified module.
Both modules and all requested names are checked before any disassembly.

Reports add `requestedSymbols` and `expectedBodyCount`. Their `bodies` sets must
exactly match the requested union, including all seven original roots. The
existing per-tool deadlines and byte limits remain; there is no automatic
recursive scan or unlimited inventory expansion. Default collection stays at
seven bodies; the maximum explicit selection produces 19 bodies.

Missing/wrong-address/failed/limited additional output produces BLOCKED, never
a roots-only PASS. Post-collection module revalidation, path confinement,
redaction, unique reports and SHA-256 recording are retained. `SYNC-001` stays
NOT RUN, all native claims stay UNPROVEN, and `privateInvocationAllowed` stays
false. Existing body validation is not a full control-flow completeness proof.

## Reproduction

Use only the exact licensed AE 25.6.0.101 modules matching `deep_targets.json`.
First run the existing default collector to obtain the inventory. Then select
an exact module/name from that report. The following variable must contain an
actually observed inventory symbol, not an invented name:

```sh
python3 -B research/ae-notifications/queue_static.py \
  --app "$EXACT_AE_APP" --output "$OWNED_RESEARCH_OUTPUT" \
  --inspect-symbol "BEE:$OBSERVED_QUEUE_SYMBOL"
```

Repeat the flag for other selected inventory names, including
`AfterFXLib:$OBSERVED_CONTEXT_SYMBOL` where appropriate. The tool does not attach,
launch AE, load Adobe code, alter security, install a plugin, or read projects.
`nm` visibility does not establish loader availability, ownership or safe ABI.

LLVM's official command reference documents Mach-O `--dis-symname` and
`--no-show-raw-insn`; it is a tooling source, not an AE API contract:
https://llvm.org/docs/CommandGuide/llvm-objdump.html (consulted 2026-09-30).
The project collector/fixture source is original; no new third-party code or
Adobe binaries/headers are added.

## Local baseline and results

Local environment: Linux, Python 3.13.5, Node 22.16.0; clang/LLVM cross-tools.
Direct repository clone was blocked by network DNS. The two files used for
local baseline testing were read through the GitHub connector and their
reconstructed bytes verified against their exact Git blob SHA:

- collector: `4b78a935fa6653563f5bed49aa5ae99ca13efb37`;
- existing tests: `b1e2f9cb88f237fb1f9da5c6b650b2cdac848bc8`.

Baseline: 23 tests, 22 PASS, one Apple-tools control NOT RUN/skipped on Linux.
The new tests were executed against the unchanged baseline before implementation:
FAIL as expected because the selection API/CLI and report fields did not exist.
This is feature-baseline evidence, not discovery of an AE defect.

After implementation:

```sh
python3 -B -m unittest discover -s tests/research -p 'test_queue*.py' -v
```

36 tests: 34 PASS, two Apple-tools controls NOT RUN/skipped on Linux. This
includes the existing actual clang/LLVM arm64 Mach-O object check and new
synthetic two-module collection/refusal/CLI tests. Syntax and whitespace checks
PASS. Tests use unique owned temporary directories and do not modify user data.

`test_real_apple_tools_collect_extra_symbol_end_to_end` builds owned arm64
libraries and executes real `dwarfdump`, `nm` and `llvm-objdump` through the full
collector. Only synthetic roots/policy are substituted; no Adobe library is
loaded. It runs automatically under the existing macOS research test discovery.
That check is NOT RUN locally; its PASS must come from exact-commit macOS CI.

Full branch TypeScript/runtime/research/build/package checks are NOT RUN locally
and are delegated to the containing commit's existing GitHub Actions gates.
No earlier SHA's CI result is claimed for this implementation. The exact source
blobs below identify local verification; CI identifies its clean checked-out
commit. No installable product artifact or release is delivered in this stage.

## Boundaries and next required evidence

Real AE collection/runtime: BLOCKED in this environment; exact Adobe modules
and an authorized AE process are absent. The Library search returned the prior
repository analysis, not a usable queue report. No new queue execution order,
thread, clone-to-UI mapping, registration ABI, unload/drainage or performance
conclusion follows from this tooling increment.

Next use an actual exact-module inventory to collect and inspect the queue
consumer/drain, clone publication/replacement and context acquisition paths.
Record per-path normal/error/cancel/shutdown behavior and unresolved indirect
calls. Only after their contracts are established should an isolated native
harness invoke any private API. LLDB remains research, not shipping delivery.
Do not keep adding synthetic tests as a substitute for the unavailable evidence.

## Verified local source identity

```json
{
  "research/ae-notifications/queue_static.py": {
    "gitBlob": "22b6022c34ed8ac0b7fb88797e78007dc2a98831",
    "sha256": "84bc973dac830272feece2181d6b0070d2d592c671b2adf1f0b03ef0040c88b4"
  },
  "tests/research/test_queue_followup.py": {
    "gitBlob": "d61d0d4b43b4e75946bc78151284d79da0512921",
    "sha256": "639583e51926e18f28c1182455f82856bd724bd4f24b4fe79590af67cf76643c"
  }
}
```
