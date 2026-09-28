# Diagnostics runtime and recovery evidence

- Test Run ID: `FSTR-CEP-DIAGNOSTICS-RUNTIME-2026-09-28-01`.
- Artifact: `fstr-cep-92fd5e97d2fa`; source and hashes in [build record](CEP-DIAGNOSTICS-2026-09-28.md).
- Environment: AE runtime reports `25.6x101`; macOS/M1 Pro environment previously recorded.
- Evidence: two user screenshots in conversation `ses_f17c04bacffdlASbDnoYNDmoaL`, before and after requested Refresh.

| Check | Status | Observed result |
| --- | --- | --- |
| Initial automatic read | FAIL | `Host returned an empty response` in both snapshot and identity display |
| Manual Refresh recovery | PASS | Subsequent screenshot shows Comp 2, 2 layers, 2 tracks, IDs 29 and 31 |
| Loaded identity | PASS | MATCH; UI and Host both `fstr-cep-92fd5e97d2fa` |
| Snapshot diagnostics display | PASS | JSON displayed, including layer name, AE index, timing frames, switches and revision |
| Exact native field comparison | NOT RUN | Screenshot does not show native numeric fields alongside diagnostics |
| Initial-read root cause / fix | NOT RUN | No reproduction or verified fix yet |

FSTR-specific CEP logs inspected: renderer log contains a CoreText compatibility message; engine log has `ClientInitialized begin/end` marked ERROR. These do not identify the cause of the empty response. A read-only AppleScript DoScript probe returned `0`, which did not provide usable JSON/host availability evidence. No host code was changed between the two screenshots. Refresh recovery does not prove a startup race or a missing JSON implementation.

Next work: reproduce initial-read failure and capture a bounded read-only bridge readiness probe before choosing a fix. Do not treat this runtime gate as fully passed based on successful manual recovery. Layer `type: unknown` shown for a solid also remains subject to field-accuracy review.
