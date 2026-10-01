# Queue evidence handoff — 2026-09-30

Test Run ID: QUEUE-KIT-20260930-01. Base:
`95207b30620dd2639224d71f3c80eba74c058217`, integration/host-safety-notifications.
Phase 0; zero of five phases accepted. Rules rechecked against main blob
`701a8c1ae3acb4dbfe1d7eda94acbf8095b88608` (unchanged).

## Baseline and bounded objective

The collector and selected-symbol support exist, but the research workflow
builds/uploads only six older kits; none includes queue_static.py. No licensed
AE modules or real queue report are available in this execution environment.
The current branch explicitly requires real data next, not more models of AE.

This increment closes the packaging gap so a single report can be obtained
from the actual Mac without installing a plug-in or attaching a debugger.
It does not extend the collector, select a private ABI or advance the phase.
Unchanged source blobs, checked locally against the connector's Git blob IDs:

- queue_static.py: `22b6022c34ed8ac0b7fb88797e78007dc2a98831`.
- deep_targets.json: `ea466547dea4b45c4e14f9a71a40167e40b38a49`.

## Criteria selected before implementation

Clean committed inputs; exact allowlisted payload and SHA-256; launcher
integrity before collection; no implicit imports from cwd/PYTHONPATH; refusal
of missing/corrupt/symlinked inputs; wrong-app refusal before host tools;
no output inside the selected application even on non-macOS refusal;
unique reports with source identity/checksum; no changed owned fixture files.
Required: local unit/syntax/whitespace checks, full exact-commit Linux/macOS
CI, and macOS smoke of the exact produced ZIP rather than a rebuild.

Production rendering, Undo, installation, SDK ABI, real AE runtime and
uninstrumented production performance are outside this offline diagnostic
increment. Their existing Phase 0 gates remain open, not waived.
Interactive picker UI: NOT RUN; AppleScript compilation and the explicit-path
CLI are separate checks. No claim of live UI acceptance follows from compilation.

## Changes and safety

`package-queue-research.py` reads five regular files from the fixed clean Git
commit, not mutable working-tree copies. The ZIP has fixed entry timestamps,
explicit Unix modes, a generated Build ID/manifest and external SHA256.txt.
An existing output directory is refused. Identity/source cleanliness is checked
again after packaging. The kit contains no Adobe binaries or SDK headers.

The launcher uses isolated Python 3.10+, verifies file bytes and the manifest,
and executes only the verified collector bytes. The file picker selects an
application bundle; it does not launch the application. An explicit --app path
bypasses UI. Nothing installs Python, Xcode or a plug-in or changes security.
The inherited module/build/UUID and bounded subprocess checks remain intact.

Each run adds sourceCommit/buildId/manifest/policy identity, saves a fresh
report.json plus SHA256.txt and wraps those two files in report.zip. No network
upload or project access occurs. The external kit checksum plus its manifest
detect accidental corruption; they are not signatures and do not protect
against a maliciously replaced bootstrap and manifest or hostile concurrent
filesystem changes. Do not disable security or strip quarantine attributes.

## Executed checks and limits

Local environment: Linux, Python 3.13.5 and git version 2.47.3;
only an exact-byte source subset was available, not a full repository checkout.
A network clone failed at DNS resolution. Full branch regression is therefore
run in GitHub Actions for the actual containing commit, not claimed locally.

`python3 -B -m unittest discover -s tests/research -p test_queue_kit.py -v`:
17 tests, 16 PASS, 1 AppleScript compilation check skipped/NOT RUN on Linux.
Bash syntax and Python AST checks PASS. Tests use fresh owned Git repositories,
actual ZIPs, actual isolated Python/bash subprocesses, Unicode/quoted paths,
repeated runs and corruption/refusal cases. These are not AE tests.

The initial launcher test exposed a real defect in the new code: the non-macOS
refusal could save its report inside an explicitly selected .app output path.
That failing test was reproduced, then the path guard was moved before platform
refusal; both Darwin and Linux branches now pass the same no-write assertion.
No guard or test was weakened. This was not a defect in the unchanged collector.

The workflow additionally packages the exact clean commit and runs
`mac_queue_kit_smoke.py` against that ZIP. It verifies the actual bash launcher,
manifest/source identity, wrong-app refusal, report checksum and unchanged
owned .app contents. The result is stored in
`dist/notification-evidence/queue-kit.json` alongside the kit ZIP and SHA256.txt.
CI results and final artifact digest are recorded in PR #2 after completion.
Historical checks for the base SHA do not substitute for the new SHA.

## Required next input / stop condition

Return one actual report.zip from the licensed AE 25.6.0.101 Mac. A BLOCKED
report is useful evidence; do not upload Adobe binaries or user projects.
After receipt: verify report checksum/source/module identity, inspect the seven
root bodies and fresh queue/context inventory, then select bounded follow-up
functions. Do not invent queue order, clone association or registration safety
from a successful collection, an exported name or a mock.

Real Adobe collection: BLOCKED here (no Mac/modules). Real delivery, queue
thread/order, clone mapping, subscriber ABI/lifetime, post-commit and coverage:
NOT RUN/UNPROVEN. No merge, deployment, release or product installation.
Rollback is a normal revert of this isolated packaging increment on the working
branch; no user environment restoration is needed because none was modified.
