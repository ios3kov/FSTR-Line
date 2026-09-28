# Static collection and real debugger tool control — 2026-09-28

Baseline: integration/host-safety-notifications at 13ea401d51f3636e2cf8eaa1e029b166c0d9f738. DEVELOPMENT_RULES.md blob a1760fde8763f789b50b91c20407938b4fcaea4a remains unchanged. This stage applies rules 3-4, 6-12, 14-16, 20-22 and 24-27. Main/PR #1 and installed AE are untouched.

## Purpose and predeclared acceptance

Remove the manual path/hash collection barrier before investigating real internal notification candidates. Retain SYNC-001 in full: genuine AE-originated changes from native UI, scripts and plugins, all required fields/contexts/playhead/Undo/Redo, post-commit availability and runtime/performance proof. No polling substitute and no fabricated callback or offset.

Acceptance: read-only collection within one explicitly selected AE 25.6 application bundle; unique identified report; no binary upload; bounded inputs/workers; wrong-version/path/link/mutation/time-limit failures explicit; private report files; source and kit hashes; every existing integration test; collector unit tests; exact diagnostic ZIP executed against an actual compiler-produced Mach-O file on macOS; UUID compared against dwarfdump; actual LLDB executes the existing callback logger against a known owned program and records exactly three expected calls. These are diagnostic-tool gates, not product/native-AE acceptance.

## Implementation

collect_app.py discovers a unique AE 25.6 bundle or accepts --app, reads CFBundleExecutable from Info.plist, prioritizes the main executable and enumerates on-disk Mach-O modules inside that bundle. Each identified module uses the existing inspector in an isolated child with timeout. Reports preserve scoped PASS/FAIL/BLOCKED, limits, source/module hashes and partial scans. They explicitly do not claim a loaded-module inventory, signature authenticity or actual AE Build 101 identity based only on plist fields.

Collect-AE.command chooses an available Python 3.10+, validates the packaged kit and produces a report ZIP in ~/Desktop/FSTR-AE-Research. It installs nothing and does not start/attach AE. Source build uses scripts/package-notification-collector.py from a clean checkout; handoff payload is staged under dist/notification-collector/<commit> with SHA-256. The native-control program and debugger harness are NOT in the user collection kit.

Reports contain selected app metadata, relative module paths and bounded string/symbol leads, not Adobe binaries or project contents. Home-user/e-mail patterns are redacted, with an explicit warning that automatic redaction is not exhaustive. Only owned temporary workers and new result files are written. No global caches, preferences, permissions, SIP, signatures or existing processes are altered.

Limits: 20,000 enumerated files, 256 modules, 8 GiB total, 2 GiB/module, 30 seconds per inspector, 300-second between-module budget, 32 MiB string scan/module, 100 leads/module. Enumeration/I/O is not a hard wall-clock process limit. External/shared/late-loaded modules and ignored symlinks remain outside the declared offline scope. No-match/limits cannot support an absence conclusion.

## Verification

Local Linux unit run: 16 new collector tests PASS, executed with Python's unittest; these use minimal fixture headers and a fake inspector, not Adobe binaries. The existing macOS workflow adds stronger independent acceptance: actual compiled Mach-O, packaged shell/Python/inspector chain, UUID comparison and real LLDB callback delivery. Commit-specific CI is authoritative; results are recorded in PR #2 with run IDs after completion. No native test is marked PASS in advance.

The LLDB harness creates and launches only tests/research/native_control.cpp, stops at its main, binds the recorder to its exact PID/module UUID/SHA, observes three calls, checks normal exit and removes its own target. On failure it can stop only the process it created, never an attached user session. Known fixture symbols are not claimed as Adobe candidates. Notification kind/post-commit fields remain UNKNOWN/NOT RUN. Debugger permission failure fails this gate rather than being hidden as a skip.

## Native AE limitation and next action

This session has a Linux container and GitHub CI access, but no exact AE application binary or authorized local Mac/AE process. Discovery of available connector capabilities did not provide a local terminal/AE connection. Real AE binary collection and candidate tracing remain BLOCKED until one run of the identified read-only collector in the user's unique AE environment provides the report. This data request is not a replacement for internal QA: the collector is first tested automatically on macOS. Then investigate real leads/cross-references, establish an AE-specific positive control and run the full coverage matrix before any production hook decision.

## References

- Apple CFBundleExecutable: https://developer.apple.com/documentation/bundleresources/information-property-list/cfbundleexecutable
- LLDB callback return/API contract: https://lldb.llvm.org/use/tutorials/breakpoint-triggered-scripts.html
- LLDB target creation/launch/breakpoints: https://lldb.llvm.org/python_api/lldb.SBTarget.html
- GitHub macOS image/toolchain inventory: https://github.com/actions/runner-images/blob/main/images/macos/macos-15-Readme.md

Sources describe packaging/tooling, not an Adobe notification API. Applicable proprietary licensing review remains required before distributing any private integration.
