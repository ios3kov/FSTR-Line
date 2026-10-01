# Observed AE bundle identifier regression — 2026-09-28

Baseline: f9090f57de4ded26aa09f7a4602f3444ae2b6778 on integration/host-safety-notifications.
DEVELOPMENT_RULES.md was rechecked at unchanged blob a1760fde8763f789b50b91c20407938b4fcaea4a. Scope: a reproduced collector identity defect; no FSTR host/UI/protocol/notification behavior changes. Main and PR #1 are untouched.

## Primary evidence and cause

User-supplied FSTR-AE-Static-20260928T212314Z-35fa34495692.zip: 781 bytes; SHA-256 146b2f75a8e6e6847ee049a09f5588d3d8d3763b563a96b5d6454e2321e55255. Exactly one report.json, 1328 bytes. Collector identity and all four source hashes match the previously handed-off f9090f5 kit.

The application was explicitly selected via the chooser. Recorded metadata:

- CFBundleIdentifier: com.adobe.AfterEffects.application
- CFBundleShortVersionString: 25.6.0
- CFBundleVersion: 25.6.0.101
- CFBundleExecutable: After Effects

The collector compared against com.adobe.AfterEffects and therefore rejected this selected application before reading any binary. This mismatch is now a reproduced cause of THIS report's failure, not an inferred missing installation or user-selection error. The first, less detailed report remains historically insufficient to prove its exact cause.

Earlier synthetic fixtures repeated the same wrong literal as the implementation. Their green CI did not validate that assumption against an independent AE identity. Correct the implementation and fixtures; do not blame the environment or waive a failed check.

## Fix and predeclared acceptance

Use exact com.adobe.AfterEffects.application equality, not startswith, wildcard, an unverified alias or skipped identity checks. Existing version, executable, path, symlink and read-only limits remain. No signature or runtime authenticity claim is made from plist data.

Add an immutable metadata-only fixture transcribed from the supplied report, with report provenance/hash and no user paths, personal data or Adobe binaries. Seven independent tests cover the observed tuple, discovery, actual inspector child on a synthetic Mach-O with the name After Effects, old/near-match ID rejection, version/binary/symlink rejection and non-runtime status.

The exact packaged macOS smoke now pairs the observed metadata and executable filename with OUR compiled C++ fixture, independently checks SHA/UUID, and retains the real LLDB 3-call positive control on the owned program. The rejected-version smoke asserts the specific version error so a wrong ID cannot masquerade as a successful version test. All prior Linux/macOS gates remain mandatory. No production artifact is modified after build.

## Executed local reproduction

Python/Linux: the seven independent tests on the exact baseline collector yielded FAIL (1 failure, 4 errors), including rejection of the observed identity. Applying only the exact ID correction yielded 7 PASS, 0 FAIL/ERROR; the synthetic binary is parsed through the actual isolated inspector child, not a precomputed reply. Local source was checked against the handed-off baseline kit hashes. Full repository checks and the exact clean kit's macOS tests are recorded separately in CI/PR #2 for the new commit; they are not assumed PASS in advance.

## Boundaries

The report contains metadata only: no actual AE module hashes, strings, symbols or runtime traces. Real AE binary collection and full direct notification source remain NOT RUN/BLOCKED until a new read-only report is available. No notification candidate is invented and no polling/revision/idle/focus/self-event substitute is accepted. This is a corrected collector, not proof of SYNC-001, real Undo/Redo, product editing or production readiness.
