# Official SDK access attempt

- Run: `FSTR-SDK-ACCESS-2026-09-28-01`.
- Scope: obtain official target SDK to unblock SYNC-001; no production changes.
- Opened `https://developer.adobe.com/console/servicesandapis/ae` in the interactive browser, not just HTTP fetch.
- Browser finished navigation but accessibility snapshots continued to show only Loading; no SDK download controls appeared.
- Also opened `https://developer.adobe.com/console/downloads`; navigation redirected to `/console/` with Loading title.
- Console contains CSP rejections for advertising/metrics resources. These are observations, not an established cause of the loading failure.
- SDK archive obtained: **BLOCKED** in this attempt.
- Version-pinned SDK headers inspected: **NOT RUN**.
- Native callback probe: **NOT RUN**.
- No proof of authentication failure or absence of a public notification API follows from this access failure.

Prepared `docs/ADOBE_NOTIFICATION_API_REQUEST.md` as a focused inquiry for Adobe. It is a draft, not submitted. Unblock by supplying the official SDK archive or an accessible official download, then inspect the headers before selecting or implementing a native adapter.
