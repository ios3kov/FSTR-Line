# Queue collector: real report and nm name collisions — 2026-09-30

Run: `QUEUE-NM-20260930-01`. Baseline: `6c22da433a747800cc473320e76cf4db4fd5eba5`.
Rules reread from main, unchanged blob `701a8c1ae3acb4dbfe1d7eda94acbf8095b88608`.
Scope: offline research collector and its tests. No private ABI, registration,
queue implementation, CEP change, host attach, installation or project access.

## Acceptance defined before the change

Reproduce the global duplicate-name refusal; allow collecting uniquely resolved
requested functions despite unrelated local collisions; preserve every distinct
address for validation; reject any ambiguous requested function before ALL
disassembly. Keep complete parsing, exact identity, symbol-table consistency,
body checks, timeout/output/path guards and all seven default roots. Preserve
bounded collision diagnostics. Run new regression controls and the existing
exact-commit Linux/macOS CI, including actual Apple-tool and exact ZIP smoke.
Real Adobe collection after the change is a separate gate, not a mock PASS.

## Received evidence, not a successful queue capture

Uploaded ZIP SHA-256: `3b61951b4046cf7367ff7a841d4c941aee9b4e7784f88c2aeaded066f3c1844a`.
Its two members are report.json and SHA256.txt; CRC and the declared checksum match.
The original redacted JSON is retained unchanged at
[evidence/queue-6c22da4-blocked.json](evidence/queue-6c22da4-blocked.json), SHA-256
`d4b1fcdc16bf18439cc277fb573a3e51e748e5351e910a7e4bd06d837e98619a`.
It contains no project data, private path or Adobe disassembly/binary.

Run `FSTR-AE-Queue-4meaj9_r`; source commit `6c22da433a747800cc473320e76cf4db4fd5eba5`;
Build ID `fstr-queue-6c22da433a74`. Verified against the previously delivered ZIP:

- manifest SHA-256 `858207f1bbc9d0d7baf1f14bb4385ca8421995be2f374cee58451c46f4098902`;
- collector SHA-256 `84bc973dac830272feece2181d6b0070d2d592c671b2adf1f0b03ef0040c88b4`;
- policy SHA-256 `1e748db1d0c565f02e23133f265b3d5768445dddabbddcf40c23114c5dee96f5`.

The report records AE 25.6.0.101 and Apple LLVM 21.0.0. Both recorded module
hashes and arm64 UUIDs match deep_targets.json. This corroborates the on-disk
identity checks recorded by this run, not the identity of a loaded AE process.
The BEE `nm -arch arm64 -U` command completed, exit 0, 9,492,430 output bytes.
Then parsing stopped with `DUPLICATE_TEXT_SYMBOL`. Neither module has a body;
no export-table comparison or disassembly completed. SYNC-001 is NOT RUN.
The old report did not keep the colliding name/addresses or raw nm text, so the
specific Adobe collision cannot be reconstructed from it. Do not invent it.

## Cause reproduced and bounded change

The baseline parser rejects a second text symbol with the same name anywhere
in a module, even when that name is unrelated to the selected functions. The
new synthetic collection control reproduces the same refusal before changes.
This reproduces the overly broad guard, not the unidentified Adobe symbol.

LLVM documents t/T as local/global code symbols and -g as the external-only
view. A plain name is not a universally unique lookup key across local symbols.
Primary reference consulted 2026-09-30:
https://www.llvm.org/docs/CommandGuide/llvm-nm.html

The collector now builds name-to-address-set tables. Repeated identical rows
refer to the same address; distinct addresses are retained, not overwritten.
The exported address set must remain a subset of the full table's set. Every
requested symbol must have exactly one address before disassembly of any symbol.
A local collision with a public symbol of the same name is therefore NOT resolved
by blindly preferring the public entry. Body label/address checks remain intact.

Unselected ambiguous leads have null address and explicit address counts in the
inventory. Reports sample at most 12 colliding names and 4 addresses per sample,
with total counts and explicit truncation. Validation still uses the complete
bounded input, not the samples. A requested conflict gets its own diagnostic.
An ambiguous target is BLOCKED, never a partial PASS or permission to call code.

## Executed local checks and exact-commit CI requirements

Linux local sources are a byte-verified subset from the delivered diagnostic
ZIP and the fetched status, not a full clone (GitHub DNS unavailable here).
Baseline new collection control: FAIL, `DUPLICATE_TEXT_SYMBOL`, as expected.
After change: 10 new tests, 9 PASS, 1 Apple-tool control NOT RUN/skipped locally.
Controls cover unrelated/same-address/requested/inventory collisions, both
modules, exported-set mismatch, bounded diagnostics, malformed input and
byte-exact preservation of the original BLOCKED evidence.

The macOS-only control compiles two owned C++ translation units into one arm64
dylib with same-named local functions, requires actual nm collision evidence,
reproduces the old strict-view refusal, then collects unique roots with actual
Apple nm/dwarfdump/objdump. No Adobe binary or SDK is involved. A local cross-link
attempt was unsupported by the container linker and is not counted as PASS.

Reproduction: `python3 -B -m unittest discover -s tests/research -p test_queue_symbol_collisions.py -v`.
All existing tests, CEP build/package, research kit builds and exact-ZIP smoke
remain mandatory in the containing commit's CI. Final run IDs, conclusions,
artifact SHA-256 and verification are recorded in PR #2 after CI, rather than
changing the already built source. A previous commit's PASS is not substituted.

## Still open

The fixed collector has NOT yet collected the user's Adobe modules. A fresh
report.zip from the checked new kit is needed; even a new BLOCKED report must
retain its actual result. Registration/context, queue order/thread, clone/UI
association, callback drainage, post-commit delivery, coverage and performance
remain UNPROVEN/NOT RUN. Issue #3 (runtime debugger shutdown) is unchanged and
not fixed by this offline collector. No merge/deploy/release or project change.
