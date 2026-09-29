# Post-commit marker Undo cleanup — 2026-09-29

Baseline 767002c. The diagnostic FSTR-PostCommit-Marker.jsx opened an Undo
group without finally. An exception while toggling the layer or recording its
state skipped endUndoGroup. This violates the controlled-test safety gate.

Added a try/finally after successful beginUndoGroup. Failure to open does not
close an unrelated group; failure to mutate still attempts closure; failure
to close does not publish after-end-undo success markers. No rollback is
claimed. If mutation and closure both throw, the closure error propagates.

Four Node VM harness tests execute the actual JSX with owned fake File/app
objects. Baseline mutation-error test failed (zero closures, expected one);
after the fix all four pass. Full Python research suite: 105 PASS. These are
controlled harness results, not AE execution. Real-AE error acceptance NOT RUN.
No installed kit or user project changed. Existing kit manifests will require
a fresh clean package for the changed JSX; old archives are not rewritten.

Next: finish the owned-session runner and fresh package before real-AE
completion correlation. SYNC-001 production acceptance remains NOT RUN.
