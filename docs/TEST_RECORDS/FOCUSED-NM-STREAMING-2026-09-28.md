# Focused nm streaming fix — 2026-09-28

User runtime evidence: Focus-AE.command from commit 743708613d57f63f8ad35712aa6ab7294ae9e501 failed before any focused report was written. The traceback is in focused_static.py -> run_text(["xcrun","nm","-nm", BEE.dylib]) with ValueError "Tool output exceeded bounded limit". This is a diagnostic-tool defect, not AE notification evidence.

Root cause: the focused tool captured the entire nm stdout/stderr in memory and applied a 4 MiB output cap before filtering. A real BEE.dylib symbol table exceeds that cap. The safety bound incorrectly applied to unfiltered intermediate output.

Scoped fix: nm is now read incrementally from an owned subprocess, irrelevant lines are discarded immediately, and only matching lines are retained. A 256 MiB hard input cap, 1 MiB line cap, timeout and 2,000-hit cap remain. Exceeding a hard cap terminates only the child nm process created by the tool. A bounded diagnostic tail is retained on nm failure. LLDB output keeps a separate 16 MiB cap. Lookup filters are narrowed to the concrete BEE/Undo/Selection/observer leads; no runtime attach, disassembly, binary modification or polling is introduced.

Predeclared regression: exact prior suite; >4 MiB irrelevant nm stream ending in one matching AE-like line; retained-hit cap; hard-input cap/owned-child termination; hash mismatch before tools; escape-path rejection; macOS exact focused kit on an owned Mach-O; integration and notification research workflows; clean source and exact artifact identity. The real user's BEE.dylib is NOT available to CI, so success on the user's exact module requires a rerun.

SYNC-001 remains NOT RUN. Passing this fix only proves that the focused collector can safely process a large symbol stream.
