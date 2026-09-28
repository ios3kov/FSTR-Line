FSTR Line — read-only AE 25.6 static collector

Run Collect-AE.command on macOS with Python 3.10+. It selects a unique AE 25.6
installation in /Applications or ~/Applications. For multiple installations:
  bash Collect-AE.command --app "/exact/After Effects.app"
The entire path must point to the application bundle, not its parent folder.

Output: ~/Desktop/FSTR-AE-Research/FSTR-AE-Static-<unique run>.zip plus SHA-256.
Share the ZIP report, NOT the Adobe application or SDK. Inspect it before sharing.
The report contains metadata, module hashes/UUIDs and bounded strings/symbol
leads. User home names and e-mail patterns in strings are redacted. Automatic
redaction is not a guarantee that every embedded sensitive string is removed.

No network requests, project edits, plug-in installation, AE launch, debugger
attach, preference/cache deletion or security changes. Only report files and
owned temporary worker files are written. No running process is terminated;
a timed-out inspector child owned by this tool may be stopped.

Limits: 20,000 files, 256 modules, 8 GiB total, 2 GiB/module, 300 seconds checked
between modules, 30 seconds/worker, 32 MiB strings/module, 100 leads/module.
The overall limit is not an OS-enforced wall-time kill; enumeration and filesystem
I/O can extend it. Symlinks and sample .aep/.aepx/.prproj files are not followed.
Shared/external and late-loaded modules are outside this offline scope. A limit
or unreadable input is explicit, never evidence that a mechanism does not exist.

PASS means the stated static collection completed, NOT that notifications work.
Plist build labels are not independently verified runtime identities. SYNC-001,
post-commit behavior and native Timeline equivalence remain NOT RUN. Research
must follow with real candidate-specific tracing and all-origin coverage.

The included build-manifest.json links these source files to a clean commit and
validates integrity. It is NOT a digital signature. This diagnostic kit is not a
FSTR Line product release or a private hook. No Adobe binary is redistributed.
