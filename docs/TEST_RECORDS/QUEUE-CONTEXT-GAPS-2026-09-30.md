# Queue context gaps — bounded offline follow-up, 2026-09-30

Baseline: `12ec6b0d46440f3259a0280d9722b480ff7b1921`.
Phase 0, 0/5 phases accepted. Rules read from main, blob
`701a8c1ae3acb4dbfe1d7eda94acbf8095b88608`. Scope is an offline collector,
its packaging and tests. No Adobe process, project, installation, private call,
production panel, main, merge, deploy or release is changed.

## Goal and acceptance fixed before implementation

Continue the concrete gaps recorded in QUEUE-ORDER-CLONE-2026-09-30.md rather
than repeat the 19-function report or add more debugger acceptance layers.
Collect the four observed context helpers and the missing four-byte command
switch table. Re-read AddFunctionToQueue only as the address/body anchor.

Required: exact existing build/hash/UUID refusal, unambiguous named functions,
bounded file-backed VM-to-file mapping, complete range and body evidence,
no arbitrary address CLI, preserved default collection, self-contained clean
package, immutable source identity, negative controls and macOS native tools.
Full branch CI and exact-ZIP macOS smoke remain mandatory before handoff.
Real Adobe collection is NOT RUN until a new user-environment report exists.

## Provenance, not guessed symbols or a callable ABI

Retained input: `FSTR-AE-Queue-qk6xsvhj`, report.json SHA-256
`f41cd06d1fd1bca74f0dc0d4085ebe1ba89dc909bea6f81ba2cec730057ae335`.
The mounted report was reread; its sidecar matches. It contains the exact call
operands below. The original archive is unchanged and is not copied into Git.

- `__Z16BEE_QueryProjectPP11BEE_Project`, call at BEE `0x777c54`.
- `__Z26BEE_GetCurrentConstProjectv`, call at `0x777c94`.
- `__ZN21BEE_ProjectSetContextC1EP11BEE_Project`, call at `0x781050`.
- `__ZN21BEE_ProjectSetContextD1Ev`, calls including `0x781074`.

The named AddFunctionToQueue begins at `0x777bfc`. Its `0x777c68`–`0x777c88`
sequence checks CommandType 0..3, reads unsigned bytes at `0xe8c4d4`, scales
by four and branches relative to `0x777c8c`. The table bytes are NOT present in
the old report. The new profile pins this address to BEE SHA-256
`817b9de9c6d57b5d6988b634842090e1528fe817a5685c8d1ff358553c6660ca`.
It does not guess table contents, enumerate undocumented CommandType values,
or claim that generic callbacks take a load-drop branch.

## Implementation

`Queue-Context.command` uses the new complete Queue kit, without a hard-coded
old directory. `queue_kit.py --context-followup` checks every packaged file
before loading the collector and range reader from the verified bytes.
The mode cannot be combined with additional symbol selection. The old default
seven-root request remains unchanged.

Both existing modules are identified before nm/disassembly. This profile then
requests exactly five BEE bodies, including the anchor; previous callback and
clone bodies are not repeated. A bounded inventory matches top-level context,
queue constructor/destructor and potential WorkQueue emitter names. Matching a
name does not prove a relationship, a callback thread or a safe registration API.

`inspect_binary.read_macho_range` reuses the existing thin/fat parser and reads
one 1..64-byte file-backed section range, with the profile fixed at four bytes.
It validates the linked arm64 slice, UUID, hash, load commands, section/segment
mapping, range uniqueness and bounds. It rejects zero-fill, arm64e, ambiguous
ranges, symlinks/FIFOs, malformed mappings and changed input. It records the
slice/file offsets, VM address, bytes and hashes. Hash/stat checks detect
persistent changes; they are not an adversarial concurrent-writer guarantee.
The file mapping is read-only and never loads or calls Adobe code.

The profile verifies the returned range and requires each computed switch
target to lie within the collected anchor body. Failure remains BLOCKED,
including when all function bodies were collected but the range failed.
All runtime/registration/coverage claims remain UNPROVEN; SYNC-001 is NOT RUN.
The old body parser still allows raw `.long` rows; this is not full CFG/decoding
acceptance. The four table bytes are evidence, not a delivery acknowledgement.

Format reference (read, not source code copied): Apple's Mach-O loader.h,
LC_SEGMENT_64 and section_64:
https://raw.githubusercontent.com/apple-oss-distributions/xnu/main/EXTERNAL_HEADERS/mach-o/loader.h
Existing parser and package machinery were reused; no third-party dependency added.

## Verification

Local Linux source-subset run: `python3 -B -m unittest discover -s tests/research
-p test_queue_context.py -v`: 20 tests, 19 PASS, one Apple-linker control NOT RUN.
Tests include thin/fat offset translation, malformed/ambiguous/zero-fill ranges,
wrong UUID/hash/architecture, symlink/FIFO refusal, change detection, missing
and ambiguous functions, both-module identity, fixed profile, anchor/range
failure, default request preservation, clean committed fixture packaging,
wrapper launch and refusal of a changed packaged reader. Bash syntax PASS.
Fixtures explicitly contain synthetic metadata, bytes and runner results.

An initial local attempt to cross-link the native control failed because the
installed Swift `ld64.lld` reports that macOS linking is unsupported. No parser
check was weakened. The real linked-Mach-O test is retained as mandatory on
macOS, not declared N/A or replaced by synthetic evidence. The exact-ZIP Mac
smoke additionally checks both entrypoints, wrong-app refusal and the packaged
reader against an actual Apple-linked arm64 dylib with known four-byte data.

The source subset came from blob-verified repository/CI sources; a complete
local clone was unavailable because github.com DNS failed. Full regression,
CEP/package checks and macOS tests belong to the containing commit's CI.
Exact run IDs, final archive hashes and outcomes are recorded in PR #2 after
completion. Earlier CI results do not validate this increment.

## Boundaries and next step

This completes preparation of a narrowly scoped offline data request, not a
shipping notification source. After exact-kit verification, obtain one report
from the licensed AE 25.6.0.101 installation and inspect the four helper bodies,
table mapping and newly discovered lifecycle/emitter names. No repeat of the
old 19-body collection is needed. Unknown callback thread/context lifetime,
UI-clone association, registration, quiescence, coverage and uninstrumented
performance stay open. Issue #3's original LLDB timeout remains open and is
not exercised by this offline kit. No new real-AE debugger handoff is approved.
