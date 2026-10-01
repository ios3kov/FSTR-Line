# Plugin-origin real run timing correction — 2026-09-29

Input: `FSTR-AE-PluginOrigin-20260929T084238Z-fcf93b543315.zip`, 4,073 bytes, SHA-256 `111c386934f41448c56b3e79908fb9b4d0f593b37d4d2b9c65d8334829f6493c`. Exact observer kit commit `d5a86afe5448882429346a07da72eecea486c193`. Observer attach/setup/clean-detach PASS.

The diagnostic helper itself is proven installed and functional:
- Build ID `fstr-plugin-origin-d5a86afe5448-20260929T084015Z`
- helper source commit matches `d5a86afe...`
- helper log contains successful public-SDK mutation `VIDEO_ACTIVE 1 → 0`
- independent state oracle also shows layer 1 video-active `1 → 0`.

However the observer action window was only about 50.6 ms:
- phase start: 1790671355751161000 ns
- phase done: 1790671355801784000 ns
- capture end: 1790671356008171000 ns

The relevant new helper mutation occurred at 1790671358478549000 ns, roughly 2.68 seconds after the observer phase had already closed and after detach. Therefore zero LLDB hits are expected and other-plugin direct-channel correlation is correctly UNPROVEN.

This is a protocol/UX timing failure, not a helper or candidate failure. A previous helper mutation in the same process is also present in the log and must not be mistaken for the current action.

Correction:
- Observe no longer waits for user Enter after the menu click.
- It records the helper log sequence baseline before starting the phase.
- After `plugin-origin-start`, it waits for a **new** `mutationEnd` with the exact installed helper Build ID and a sequence greater than the baseline.
- It then keeps the LLDB window open for a bounded 1.5-second downstream grace period before writing `plugin-origin-done`.
- The detected mutation is rejected if its wallTimeNs somehow falls outside the resulting action window.
- A 60-second bounded timeout and child-process exit checks prevent indefinite waiting.
- This observer kit explicitly accepts the already installed helper source commit `d5a86afe...`; no rebuild/reinstall is required.

Next user action is therefore only a repeat of `Observe.command` from the updated kit, with one click on Window → FSTR Plugin Origin Test and **no Enter after the click**.
