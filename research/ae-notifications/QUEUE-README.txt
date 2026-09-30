FSTR: read-only queue/context diagnostic kit (not a plug-in or release)

Purpose: collect real static evidence for AE 25.6.0.101 on macOS arm64.
No AE startup, debugger attach, native function call, installation, network
upload, security change, preference cleanup or project access is performed.
A running AE session need not be closed. Do not edit/update the AE application
bundle while collection is running. This kit does not prove SYNC-001 delivery.

Run Queue-AE.command and select the Adobe After Effects 2025 .app in the file
picker. It selects a file, not an application to launch. Python 3.10+ and Apple's
command-line tools must already be available; this kit installs nothing.
The terminal prints the exact path to a new report.zip under
~/Desktop/FSTR-AE-Research/FSTR-AE-Queue-<unique-id>/.
Return that report.zip, including a BLOCKED report. Do not send Adobe binaries.

An explicit-path, non-interactive invocation is also supported:
bash Queue-AE.command --app "/exact/path/to/After Effects.app" --output "/owned/output"
Verify without inspecting any app: bash Queue-AE.command --verify-only

The outer SHA256.txt identifies the exact kit ZIP. The embedded manifest binds
its files to a clean source commit; it detects accidental loss/corruption, not
malicious replacement of both the launcher and its manifest. This is not a
signed/notarized product. Do not disable macOS security or remove quarantine
attributes to run it. If the OS refuses, retain that error for diagnosis.

Reports contain version/hash/UUID, symbol names, bounded disassembly, tool
results and source identity, not project names, layers, footage or full Adobe
binaries. Selected application/home paths are redacted by the collector.
Inspect report.json before sharing. Nothing is sent automatically.
Each run creates a new folder; prior reports are not overwritten.
PASS describes collection completeness only. Runtime queue order/thread,
clone association, callback lifetime/ABI and production delivery stay UNPROVEN.
The interactive file-picker UI and collection on licensed Adobe modules require
the actual Mac; CI verifies the CLI, picker syntax and owned controls separately.

CONTEXT FOLLOW-UP (qk6xsvhj research continuation)
Run Queue-Context.command from this new self-contained kit. No old kit is needed.
The exact AE 25.6.0.101 module hashes/UUIDs remain mandatory. It collects four
previously observed context helpers, AddFunctionToQueue as its table anchor,
and exactly four file-backed bytes at the pinned command-table address.
It does NOT repeat the prior 19-body request. The anchor is intentionally reread.
No Adobe code is invoked; the data does not approve native calls or shipping.
The report also inventories narrowly matched context/queue lifecycle and emitter
names. Names are leads, not proof of a notification source or an external ABI.
Missing/ambiguous functions, invalid address mapping, hash changes or an incomplete
range block the whole collection. Raw VM-address CLI selection is not supported.
Return report.zip, not any Adobe binaries. The picker never starts After Effects.

CONTEXT IMPLEMENTATIONS (2mniyqyl research continuation)
Run Queue-Details.command from this self-contained kit. No old directory is used.
Eight exact names from the latest report are requested: the C2/D2 context bodies,
context accessors/default constructor, queue constructor/destructor, and the
observed speculative-preview change function. The earlier C1/D1 bodies are only
one-instruction forwarding branches; their implementation contracts remain open.
No root bodies, query helpers, AddFunctionToQueue or table bytes are repeated.
Both module identities and every requested symbol are checked before disassembly.
The bounded inventory now includes top-level WorkQueue names to locate setup and
emitter leads; names do not prove callback coverage, main-thread execution or ABI.
Profiles cannot be combined; additional arbitrary symbol selections are refused.
PASS means those eight bodies were collected, not that subscription is safe.
