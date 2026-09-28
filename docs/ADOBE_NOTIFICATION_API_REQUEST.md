# Adobe SDK clarification request — draft, not submitted

## Subject

AE 25.6: supported push notifications for native Timeline changes (AEGP / CEP)

## Request

We are developing FSTR Line, a read model and alternative UI over native After Effects layers. AE remains the sole project and rendering authority. Target: AE 25.6.0.101 on macOS Apple Silicon, CEPHtmlEngine 12.0.1.2.

We need a supported subscription/callback that reports native Timeline changes without periodic project/layer scans or revision polling. Could you identify the public SDK suite, version, header, registration function and sample for the following?

1. Layer timing: startTime, inPoint, outPoint.
2. Layer creation, deletion and reordering.
3. Selection, visibility, solo, lock, audio and label changes.
4. Active composition changes, project open/close and playhead changes.
5. Undo/Redo and edits originating from scripts or other plugins, not just menu commands or our own UI.

We found CEP CSEvent/PlugPlug transport and AEGP command, menu-update and idle hooks, but no documented complete project-change notification stream. Idle callbacks, UI focus changes, revision queries and render-item timestamp checks do not satisfy this requirement.

If callbacks are available, please clarify:

- delivery thread and which suites are safe in the callback;
- whether delivery occurs during a drag or after commit;
- affected layer/composition IDs and deletion identity lifetime;
- notification coalescing and ordering relative to Undo/Redo;
- callbacks for selection/playhead changes that do not affect rendered output;
- supported SDK package for AE 25.6 and minimum host version.

If the public API does not expose this, please confirm the limitation and whether an additional supported Adobe integration is available. We do not want to depend on private symbols or present polling as native notifications.

## Acceptance evidence needed

A reference to a supported API and a target-host test covering each change category. A native plugin or custom event transport alone is not evidence of host change detection.
