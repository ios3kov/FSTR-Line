# Final one-run matrix plan — 2026-09-29

User requested all remaining user-facing checks in one invocation instead of separate v6/v7/v8 runs.

The new Runtime-AE.command runs one outer parent process and two bounded LLDB observation sessions separated by a **manual** AE restart/reopen. The tool never quits or launches After Effects itself.

Pre-restart interactive matrix:
idle; native move/trim; add; delete; reorder; selection; switch; Undo; Redo; active-comp switch; playhead; automatic ExtendScript structural mutation; automatic 20-operation ExtendScript burst; rapid native 10-switch burst; optional third-party-plugin mutation; idle.

Then the observer clean-detaches. The user saves/closes AE manually, presses Enter, reopens the same exact AE build + saved test project, presses Enter, and the parent attaches a second session:
idle; move/trim; Undo; Redo; playhead; automatic ExtendScript structural mutation; idle.

Independent state evidence:
a bundled read-only ExtendScript snapshot is collected outside every action window, before START and after DONE. It records active comp/layer count/time/selection and bounded layer state. This confirms the resulting state visible after an action but **does not prove that breakpoint entry itself is post-commit**.

Origin automation:
macOS uses the documented AppleScript DoScriptFile bridge to execute bundled ExtendScript against the already-running AE instance. If automation permission/script invocation fails, Terminal provides the exact bundled JSX path for manual Run Script File fallback inside the same run.

Stress/performance:
FSTR-Burst.jsx performs 20 reversible enabled-toggle assignments. Parent records wall-clock AppleScript execution once before LLDB attach and once while observed; the report stores raw ms and ratio. A separate manual 10-click switch burst provides native multiplicity evidence. Counts are raw fanout/miss evidence and are not automatically labeled duplicate notifications.

Other-plugin origin:
the same run includes an optional third-party-plugin phase. If the user has a plugin that actually mutates the active layer/comp, they perform one mutation. If not, Enter with no action keeps this origin visibly unproven/BLOCKED. No helper plugin is silently installed and no third-party plugin is modified.

Restart/reopen:
the outer launcher requires zero matching AE processes after the user's manual close, then a single exact matching process after manual reopen. A fresh LLDB session is attached and the post-restart subset is repeated. No SIP/signing/system setting change is allowed.

Acceptance before handoff: 68+ research regressions plus new final-matrix unit tests, exact clean package, existing native/focused controls, parent↔LLDB IPC attach smoke, push+PR Linux/macOS PASS, exact artifact hash. SYNC-001 remains NOT RUN until resulting evidence is analyzed; this package is designed to avoid asking the user for another matrix run unless a genuinely unsupported origin remains.
