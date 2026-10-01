# Final Matrix analysis — real AE 25.6.0.101 — 2026-09-29

Input: `FSTR-AE-FinalMatrix-20260929T072338Z-2daebc3abe79.zip`, SHA-256 `12f0de676336fe2fc61dd6f8692b77d5d52e32cec67fef3c542009b58ad5d2d4`. Build: clean `97c3f8a6636ef12cc1b60f0093c598b5259141ab`, Build ID `fstr-final-matrix-97c3f8a6636e`.

Both real AE observer sessions are PASS and clean-detached. Pre-restart PID 80268; post-restart PID 96103. The restart/reopen gate is therefore observed with a new process.

Strict start/done-window counts for `process-project-changes`:
- native move/trim 14
- layer add 14
- layer delete 6
- layer reorder 6
- selection 2
- layer switch 4
- Undo 1
- Redo 1
- active-comp switch **0**
- playhead 29
- ExtendScript structural scenario 12
- ExtendScript 20-toggle burst 20
- native 10-click switch burst 30
- optional other-plugin window 11 (provenance NOT established)
- both pre-restart idle windows 0
- post-restart timing 14, Undo 1, Redo 1, playhead 17, ExtendScript 12, idle windows 0.

This establishes a strong common native/script project-change path for the tested operations. It does **not** establish one event per logical mutation; native rapid switch produced multiple process hits per click. It also does not prove third-party-plugin provenance from the optional window.

Ordering: for timing/add/delete/reorder/selection/switch/Undo/Redo/playhead and the normal ExtendScript scenario, the last `DoProcessProjectChanges` hit in each action window occurred after every known mutation/transaction marker instrumented in that window. The ExtendScript burst is a counterexample: end-group/render/layer-switch markers occurred after the last process hit. Therefore the function's entry cannot be declared universally post-commit from this evidence.

State oracle failure: every macOS DoScriptFile snapshot returned literal `0`, so the Final Matrix did not capture the intended project-state string. Post-action state verification is invalid and post-commit remains UNPROVEN.

Active-comp gap: switching the active composition produced zero instrumented candidate hits. A separate direct channel is still required for active composition/viewer context changes.

Performance: the report records baseline 194.577 ms and observed 2836.678 ms for the 20-operation ExtendScript burst (14.579x under LLDB observation). This is debugger/research overhead evidence only, not a production-hook performance estimate.

Formal status:
- common native mutation path: OBSERVED
- ExtendScript origin: OBSERVED
- restart/reopen: OBSERVED
- active-comp direct source: GAP
- other-plugin origin: UNPROVEN
- post-commit semantics: UNPROVEN
- SYNC-001: NOT RUN / not accepted.

Next research gate is static-only first: bounded exact-build disassembly of `DoProcessProjectChanges` to identify downstream dispatcher/signal calls, plus exact-symbol discovery for active-comp activation. No additional broad runtime matrix is justified until these static leads are resolved.
