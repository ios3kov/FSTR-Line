#!/usr/bin/env python3
"""Read-only completion research preflight. Never attaches, launches or runs JSX."""
import argparse
import json
from pathlib import Path
import platform
import sys
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import context_probe
import deep_static


def preflight(app, pid):
    if type(pid) is not int or pid <= 0:
        raise ValueError("An explicit positive PID is required")
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise ValueError("Completion targets require macOS arm64")
    targets = json.loads((ROOT / "completion_targets.json").read_text())
    app, binary, meta = context_probe.exact_identity(Path(app), targets)
    if context_probe.find_pid(binary) != pid:
        raise ValueError("Selected AE PID does not match explicit test PID")
    modules = []
    for key, spec in targets["modules"].items():
        path, evidence = deep_static.verify_module(app, key, spec)
        if path is None:
            raise ValueError("Exact module identity mismatch: " + key)
        modules.append(evidence)
    # Hashing takes time. Refuse if the selected process changed meanwhile.
    if context_probe.find_pid(binary) != pid:
        raise ValueError("Selected AE PID changed during preflight")
    return {"kind": "completion-preflight", "status": "PASS", "pid": pid,
            "checkedAtNs": time.time_ns(), "application": meta, "modules": modules,
            "targetCount": len(targets["breakpoints"]),
            "targetDefinitionSha256": deep_static.sha256(ROOT / "completion_targets.json"),
            "attachAllowed": False, "projectOwnership": "UNVERIFIED",
            "loadedModuleIdentity": "NOT VERIFIED", "SYNC-001": "NOT RUN",
            "limitations": ["On-disk identity and PID selection only; not attach authorization.",
                            "PID reuse and process changes after checking remain possible.",
                            "No project inspection, runtime capture or shipping acceptance."]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--pid", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        report = preflight(args.app, args.pid)
    except (ValueError, OSError, RuntimeError, context_probe.Blocked) as error:
        report = {"kind": "completion-preflight", "status": "BLOCKED",
                  "error": str(error), "attachAllowed": False, "SYNC-001": "NOT RUN"}
    print(json.dumps(context_probe.collect_app.redact(report), indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
