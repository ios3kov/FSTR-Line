# Direct Timeline notifications — research gate

Date: 2026-09-28. Target: AE 25.6.0.101 / CEP 12 / macOS Apple Silicon.

## Requirement and result

Authoritative product requirement: **SYNC-001 — «Наша панель тоже должна получать изменения напрямую»**, acceptance criteria in `docs/PRODUCTION_PLAN.md`. Research limitations do not waive this requirement.

The user requires AE-originated notifications for native Timeline changes, rather than periodic full layer reads. No perceptible UI/playback degradation is the performance goal; zero resource usage is not a realistic guarantee.

**Result: implementation BLOCKED pending a verified event source.** Reviewed public documentation does not establish a complete Timeline change subscription for this target. This is not proof that no Adobe/private/future API exists. A native rewrite is not justified by the evidence yet.

## Sources inspected

1. [Adobe CEP 12 Cookbook](https://github.com/Adobe-CEP/CEP-Resources/blob/master/CEP_12.x/Documentation/CEP%2012%20HTML%20Extension%20Cookbook.md), CEP Events / Standard Events / invoking scripts. Official Adobe repository. CSEvent/PlugPlug provide transport; events require a producer. Standard host-event table has no AE column. This table cannot establish AE document or layer notification support. evalScript runs on the host main thread.
2. [AEGP Suites guide](https://ae-plugins.docsforadobe.dev/aegps/aegp-suites/), Register Suite / Command Suite / Render Suite. Community-maintained SDK guide, not a version-pinned AE 25.6 SDK. RegisterCommandHook concerns commands, RegisterUpdateMenuHook menu updates, RegisterIdleHook sporadic idle callbacks. None is documented here as a complete layer-change stream. AEGP_HasItemChangedSinceTimestamp queries video changes, not a push callback for every Timeline field.
3. [Project.revision](https://ae-scripting.docsforadobe.dev/general/project/#projectrevision). Read-only revision counter; reading it repeatedly is still polling. No per-layer event payload or subscription is documented there. Selection/context/playhead coverage must not be inferred from the revision description.
4. [Adobe AE developer portal](https://developer.adobe.com/after-effects/) links to [SDK Console](https://developer.adobe.com/console/servicesandapis/ae). The HTTP fetch returned a JavaScript loading shell, not an SDK archive. No AE_GeneralPlug.h found in the scoped Documents/Downloads search (maximum depth 5). Thus target-version header verification and native probe are NOT RUN. No claim of account authorization failure is made.

## Required coverage

| Change originating in AE | Verified public push API for AE 25.6 |
| --- | --- |
| Move, trim, start/in/out changes | Not established |
| Layer add/delete/reorder | Not established |
| Selection and layer switches | Not established |
| Active composition/project switch or close | Not established |
| Undo/Redo, including changes from scripts/plugins | Not established |
| Playhead changes | Not established |

Focus events, keyboard/mouse interception, menu hooks, a timer sending custom CSEvents, and revision polling do not satisfy this contract. Events emitted by FSTR's own operations would cover only FSTR-originated edits, not native Timeline edits.

## Architecture decision

- Keep Core/Host/UI separation and AE as source of truth.
- Existing opt-in Auto Sync (2s) is an experimental polling prototype and does **not** satisfy this requirement. It is off by default; no performance acceptance exists.
- Do not implement a guessed listener name, replace the adapter with native code, or claim event-based sync before proving event coverage.
- Discovery retries are separately scoped startup recovery, also not Timeline notifications.

## Unblock procedure

Obtain an official SDK applicable to AE 25.6 through Adobe Developer Console; record version/hash and inspect registration suites/headers/samples. If a candidate callback exists, create an isolated read-only native probe: timestamp callback delivery and affected IDs, without scanning layers on idle. Exercise every matrix row, including Undo/Redo and script-originated edits. Record missed/duplicate notifications, main-thread cost, idle calls and playback latency. Only then select native-to-CEP transport and targeted snapshot invalidation. If headers expose no candidate, request Adobe developer clarification with this coverage matrix; do not silently substitute polling.

This research stage changes documentation only. No runtime compatibility or performance PASS follows from it.
