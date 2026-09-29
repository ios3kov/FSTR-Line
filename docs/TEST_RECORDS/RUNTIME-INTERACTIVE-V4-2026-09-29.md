# Runtime v4 — Enter-driven interactive protocol — 2026-09-29

User feedback on v3: audible commands did not occur in their environment and long timer gaps made the workflow awkward. The requested contract is explicit: show one action, user performs it, then presses Enter; only then advance.

Runtime v4 removes timed human phases entirely. After exact AE/module identity verification and breakpoint setup, the target is paused and Terminal asks for Enter to start. Then for each phase the observer writes a START phase marker, shows one Russian instruction in /dev/tty, waits for Enter, and only after that writes the DONE marker and displays the next action. There is no fixed delay between actions.

Safety/bounds:
- initial and per-step Enter wait are each bounded to 60 seconds by select() on /dev/tty;
- timeout/error routes through the existing clean stop/detach path;
- total capture remains bounded by the existing 540-second outer limit;
- CI/noninteractive fixture path remains available only through the test plan; the user package is configured interactive=true;
- no voice dependency, AppleScript UI automation, key injection, target expressions, target private calls or project-variable reads are added.

The breakpoint set remains the correlation-v3 exact-address set: BEE transaction/content boundaries, Undo/selection/switch candidates and AfterFX native action/playhead markers. Every user action now has unambiguous start/done delimiters.

Predeclared gates: new pure unit tests for Enter gating/order/timeout/validation; all existing research/integration tests; exact package; macOS exact-address labeled attach smoke with stack metadata and clean detach; clean source; push and PR Linux/macOS PASS before handoff.

SYNC-001 remains NOT RUN.
