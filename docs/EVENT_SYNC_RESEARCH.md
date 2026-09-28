# Direct Timeline notifications — research gate

Date: 2026-09-28. Target: AE 25.6.0.101 / CEP 12 / macOS Apple Silicon.

## Requirement and result

Authoritative product requirement: **SYNC-001 — «Наша панель тоже должна получать изменения напрямую»**, acceptance criteria in `docs/PRODUCTION_PLAN.md`. Research limitations do not waive this requirement.

The user requires AE-originated notifications for native Timeline changes, rather than periodic full layer reads. No perceptible UI/playback degradation is the performance goal; zero resource usage is not a realistic guarantee.

**Result: implementation BLOCKED pending a verified event source.** The official AE 25.6 SDK headers were inspected and do not expose a complete Timeline change subscription for this target. This is not proof that no private/future API exists. A native rewrite is not justified by the evidence yet.

## Sources inspected

1. [Adobe CEP 12 Cookbook](https://github.com/Adobe-CEP/CEP-Resources/blob/master/CEP_12.x/Documentation/CEP%2012%20HTML%20Extension%20Cookbook.md), CEP Events / Standard Events / invoking scripts. Official Adobe repository. CSEvent/PlugPlug provide transport; events require a producer. Standard host-event table has no AE column. This table cannot establish AE document or layer notification support. evalScript runs on the host main thread.
2. [AEGP Suites guide](https://ae-plugins.docsforadobe.dev/aegps/aegp-suites/), Register Suite / Command Suite / Render Suite. Community-maintained SDK guide, not a version-pinned AE 25.6 SDK. RegisterCommandHook concerns commands, RegisterUpdateMenuHook menu updates, RegisterIdleHook sporadic idle callbacks. None is documented here as a complete layer-change stream. AEGP_HasItemChangedSinceTimestamp queries video changes, not a push callback for every Timeline field.
3. [Project.revision](https://ae-scripting.docsforadobe.dev/general/project/#projectrevision). Read-only revision counter; reading it repeatedly is still polling. No per-layer event payload or subscription is documented there. Selection/context/playhead coverage must not be inferred from the revision description.
4. [Adobe AE developer portal](https://developer.adobe.com/after-effects/) links to [SDK Console](https://developer.adobe.com/console/servicesandapis/ae). The HTTP fetch returned a JavaScript loading shell, not an SDK archive. No AE_GeneralPlug.h found in the scoped Documents/Downloads search (maximum depth 5). Thus target-version header verification and native probe are NOT RUN. No claim of account authorization failure is made.

5. **Official After Effects Plug-in SDK 25.6, Mac OS, downloaded by the user.** Archive SHA-256: `e02fa2b488c3cceb238866b648eb9a2526d308a260744367915a2f173663c36c`. The Zstandard payload was extracted to a controlled temporary audit directory. `Examples/Headers/AE_GeneralPlug.h` contains `AEGP_RegisterCommandHook`, `AEGP_RegisterUpdateMenuHook`, `AEGP_RegisterDeathHook`, and `AEGP_RegisterIdleHook`; it contains no Timeline/project/layer change-notification registration function. `AEGP_GetCurrentTimestamp` and `AEGP_HasItemChangedSinceTimestamp` are in `AEGP_RenderSuite5`; the header describes them as a render timestamp and a query for whether an item's video changed since that timestamp. They are not push callbacks and do not cover audio, selection, ordering, layer switches, or playhead changes. SDK version/header inspection is PASS; native runtime probe is NOT RUN.

6. Candidate audit: `docs/TEST_RECORDS/DIRECT-NOTIFICATION-CANDIDATES-2026-09-28.md`. This checks `PF_AdvItemSuite1`, ADM notifier references, CEP transport, and `AEGP_Command_ALL`. Only the command hook remains a partial candidate; none is currently a complete source.

## Required coverage

| Change originating in AE | Verified public push API for AE 25.6 |
| --- | --- |
| Move, trim, start/in/out changes | No push API in inspected AE 25.6 headers |
| Layer add/delete/reorder | No push API in inspected AE 25.6 headers |
| Selection and layer switches | No push API in inspected AE 25.6 headers |
| Active composition/project switch or close | No push API in inspected AE 25.6 headers |
| Undo/Redo, including changes from scripts/plugins | No push API in inspected AE 25.6 headers |
| Playhead changes | No push API in inspected AE 25.6 headers |

Focus events, keyboard/mouse interception, menu hooks, a timer sending custom CSEvents, and revision polling do not satisfy this contract. Events emitted by FSTR's own operations would cover only FSTR-originated edits, not native Timeline edits. `AEGP_Command_ALL` is tracked as a partial candidate and cannot be accepted without post-commit matrix evidence.

## Architecture decision

- Keep Core/Host/UI separation and AE as source of truth.
- Existing opt-in Auto Sync (2s) is an experimental polling prototype and does **not** satisfy this requirement. It is off by default; no performance acceptance exists.
- Do not implement a guessed listener name, replace the adapter with native code, or claim event-based sync before proving event coverage.
- Discovery retries are separately scoped startup recovery, also not Timeline notifications.

## Unblock procedure

Interactive SDK Console access was also attempted: see `docs/TEST_RECORDS/SDK-ACCESS-2026-09-28.md`. Download controls did not load; target SDK remains unavailable. A precise Adobe clarification draft is prepared in `docs/ADOBE_NOTIFICATION_API_REQUEST.md` (not submitted).

Obtain an official SDK applicable to AE 25.6 through Adobe Developer Console; record version/hash and inspect registration suites/headers/samples. If a candidate callback exists, create an isolated read-only native probe: timestamp callback delivery and affected IDs, without scanning layers on idle. Exercise every matrix row, including Undo/Redo and script-originated edits. Record missed/duplicate notifications, main-thread cost, idle calls and playback latency. Only then select native-to-CEP transport and targeted snapshot invalidation. If headers expose no candidate, request Adobe developer clarification with this coverage matrix; do not silently substitute polling.

This research stage changes documentation only. No runtime compatibility or performance PASS follows from it.
