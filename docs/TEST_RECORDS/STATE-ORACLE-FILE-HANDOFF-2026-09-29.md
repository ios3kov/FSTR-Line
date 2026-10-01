# State oracle file handoff — 2026-09-29

Final Matrix exposed an architectural bug in the read-only state oracle: macOS After Effects `DoScriptFile` returned the AppleEvent status value `0`, not the JSX expression return string. Every historical snapshot therefore contained `value="0"` and could not prove resulting project state.

Correction:
- `FSTR-Snapshot.jsx` no longer returns state through AppleScript.
- The parent creates a unique mode-0700 snapshot directory inside its already-owned Final Matrix workspace.
- A copy of the snapshot JSX reads a sibling `snapshot-target.txt` containing the unique owned output path and writes the bounded state string directly to that file.
- Python accepts a snapshot only when the AppleScript bridge completed successfully AND the unique output exists, is a regular non-symlink file inside the owned snapshot directory, is <=64 KiB, and is non-empty.
- The AppleScript stdout value is explicitly ignored for state.
- No project write is performed; the JSX reads active comp/layer metadata only.

This fixes the oracle implementation for the next narrow runtime positive control. It does not retroactively validate the historical Final Matrix snapshots and therefore does not change post-commit status: still UNPROVEN.

Predeclared regressions: a mocked AppleScript success returning stdout `0` must still obtain state from the owned file; a bridge success with no output file must be rejected as an invalid oracle. All existing research/integration/macOS gates remain required.
