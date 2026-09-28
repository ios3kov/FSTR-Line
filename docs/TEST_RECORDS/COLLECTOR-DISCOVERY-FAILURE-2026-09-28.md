# AE collector discovery failure and recovery — 2026-09-28

## User evidence, not an AE absence result

Input: `FSTR-AE-Static-20260928T210957Z-8858e0b53bef.zip`, 616 bytes,
SHA-256 `1ea81cc83059bed44a42df0786f25280c57ffccf3169d274145551aead188b1b`.
One entry, `report.json` (785 bytes), `collectionStatus=BLOCKED`, reason
`No unique AE 25.6 installation found. Pass --app with the exact .app path`.
No application metadata, modules, symbols or traces are present. `SYNC-001=NOT RUN`.
Collector identity matches the retained verified 7b21e50 kit, including all four
source-file hashes. This establishes which collector ran, not why discovery failed.

The baseline catches candidate validation failures without recording them and
returns the same message for zero/multiple accepted candidates. The supplied
report cannot distinguish an unsearched path, multiple installations, metadata
mismatch or a read/validation error. None is asserted as the user's actual cause.
No Adobe event candidate can be inferred from this input.

## Scoped fix and acceptance declared before testing

Continue integration/host-safety-notifications from 7b21e50; main and PR #1 stay
unchanged. DEVELOPMENT_RULES.md blob a1760fde8763f789b50b91c20407938b4fcaea4a
was rechecked; apply baseline, safe automation, identity, regression and evidence
rules. Scope is collector selection/diagnostics only, not product editing or sync.

- Default .command launch opens a macOS Standard Additions application file chooser;
  the selected application is not launched. Explicit --app remains noninteractive.
- CLI auto discovery records NOT_FOUND / AMBIGUOUS / INCOMPLETE and bounded
  AE-related candidate metadata/rejection reasons. It does not emit an inventory
  of unrelated applications. --non-interactive never opens a dialog.
- A selected but rejected app retains the four allowlisted plist fields and the
  specific failure. This is diagnostic evidence, not permission to scan another
  product/version. Bundle/version/symlink/read-only guards are NOT weakened.
- Cancellation, timeout and invalid selection do not start collection. Kit hashes
  are checked before the chooser. Existing project/preferences/security boundaries
  and all scan/worker limits are unchanged.

Predeclared automated gates: all existing Linux/macOS tests; 14 new selection tests
(path/metadata/ambiguity/privacy/cancel/error/kit integrity); exact generated kit
run with an explicitly chosen incompatible fixture on macOS (metadata preserved,
no module reads); compile the exact chooser AppleScript with Apple's osacompile;
existing real Mach-O/UUID and LLDB owned-fixture checks; exact kit SHA and clean
source. A live human interaction with the chooser is not automated and is NOT RUN;
script compilation and mocked selection do not prove that interaction. --app is
the existing, independently executed non-GUI route.

Local 14 selection tests: PASS on Python/Linux. Actual repository regression and
macOS gates are recorded for this commit in CI/PR after running, not pre-labelled
as passing. Historical 7b21e50 results remain unchanged. Test fixtures are not
Adobe binaries; no AE compatibility or notification evidence follows.

## Current result / next evidence

The input proves a collector discovery failure, not that AE is absent or that an
internal event mechanism does not exist. The next bounded data collection chooses
the actual .app explicitly; even metadata rejection now returns actionable data.
Actual AE binary/dispatch investigation, post-commit delivery, all native/script/
plugin origins and performance remain NOT RUN. SYNC-001 remains mandatory, with
no polling/revision/idle/focus/self-event substitute. No source/hook is fabricated.

Primary reference for the chooser: Apple Mac Automation Scripting Guide,
"Prompting for Files or Folders", choose file with a type identifier:
https://developer.apple.com/library/archive/documentation/LanguagesUtilities/Conceptual/MacAutomationScriptingGuide/PromptforaFileorFolder.html
This documents the file chooser, not an AE notification API.
