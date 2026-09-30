#!/usr/bin/env python3
"""Verify the diagnostic kit before collecting read-only queue/context evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import stat
import subprocess
import types
import zipfile
from pathlib import Path

FILES = ("Queue-AE.command", "queue_kit.py", "queue_static.py", "deep_targets.json", "QUEUE-README.txt",
         "inspect_binary.py", "Queue-Context.command")
MAX_FILE = 8 * 1024**2
CHOOSER = '''try
  set chosenApp to choose file of type {"com.apple.application-bundle"} with prompt "Select Adobe After Effects 2025 for read-only inspection (no launch)"
  return POSIX path of chosenApp
on error number -128
  return ""
end try'''


class KitError(ValueError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_regular(path: Path) -> bytes:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= MAX_FILE:
        raise KitError("INVALID_KIT_FILE")
    with path.open("rb") as source:
        data = source.read(MAX_FILE + 1)
    if len(data) != info.st_size:
        raise KitError("KIT_FILE_CHANGED")
    return data


def verify_kit(root: Path) -> tuple[dict, dict[str, bytes]]:
    raw = read_regular(root / "build-manifest.json")
    manifest = json.loads(raw)
    if (not isinstance(manifest, dict) or manifest.get("schemaVersion") != 1 or
            manifest.get("sourceState") != "clean" or
            not isinstance(manifest.get("sourceCommit"), str) or
            not re.fullmatch(r"[0-9a-f]{40}", manifest["sourceCommit"]) or
            manifest.get("buildId") != "fstr-queue-" + manifest["sourceCommit"][:12] or
            not isinstance(manifest.get("files"), dict) or set(manifest["files"]) != set(FILES)):
        raise KitError("INVALID_KIT_MANIFEST")
    payload = {}
    for name in FILES:
        expected = manifest["files"][name]
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise KitError("INVALID_KIT_HASH")
        payload[name] = read_regular(root / name)
        if sha(payload[name]) != expected:
            raise KitError("KIT_HASH_MISMATCH:" + name)
    manifest["manifestSha256"] = sha(raw)
    return manifest, payload


def choose_application() -> Path:
    result = subprocess.run(["/usr/bin/osascript", "-e", CHOOSER], capture_output=True,
                            text=True, timeout=120, check=False)
    if result.returncode or len(result.stdout) > 4096:
        raise KitError("APPLICATION_SELECTION_FAILED")
    selected = result.stdout.rstrip("\r\n")
    if not selected:
        raise KitError("APPLICATION_SELECTION_CANCELLED")
    return Path(selected)


def main(argv=None, *, root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true", help="verify kit without inspecting any application")
    parser.add_argument("--app", type=Path, help="explicit .app path; otherwise show a file picker on macOS")
    parser.add_argument("--output", type=Path, default=Path.home() / "Desktop/FSTR-AE-Research")
    parser.add_argument("--inspect-symbol", action="append", default=[], metavar="MODULE:SYMBOL")
    parser.add_argument("--context-followup", action="store_true",
                        help="collect the pinned context helpers and four-byte command table")
    args = parser.parse_args(argv)
    root = (root or Path(__file__).parent).resolve()
    try:
        manifest, payload = verify_kit(root)
    except (OSError, ValueError, TypeError) as error:
        reason = str(error) if isinstance(error, KitError) else type(error).__name__
        print("BLOCKED: " + reason + "; no application inspected")
        return 2
    identity = {key: manifest[key] for key in ("sourceCommit", "sourceState", "buildId", "manifestSha256")}
    if args.verify_only:
        print(json.dumps({"kitStatus": "PASS", **identity, "SYNC-001": "NOT RUN"}))
        return 0
    # Execute the already hash-verified bytes, not an import from cwd/PYTHONPATH.
    collector = types.ModuleType("_fstr_queue_collector")
    collector.__file__ = str(root / "queue_static.py")
    exec(compile(payload["queue_static.py"], collector.__file__, "exec"), collector.__dict__)
    report = {"collectionStatus": "BLOCKED", "SYNC-001": "NOT RUN", "privateInvocationAllowed": False}
    try:
        # Refuse writes inside an explicitly selected bundle on EVERY platform,
        # including a blocked non-macOS run which still saves a diagnostic.
        if args.app is not None and args.output.expanduser().resolve().is_relative_to(args.app.expanduser().resolve()):
            print("BLOCKED: OUTPUT_INSIDE_APPLICATION; no files written")
            return 2
        if platform.system() != "Darwin":
            raise KitError("MACOS_REQUIRED")
        app = args.app if args.app is not None else choose_application()
        app = app.expanduser().resolve()
        if args.output.expanduser().resolve().is_relative_to(app):
            print("BLOCKED: OUTPUT_INSIDE_APPLICATION; no files written")
            return 2
        policy = json.loads(payload["deep_targets.json"])
        if args.context_followup:
            reader = types.ModuleType("_fstr_range_reader")
            reader.__file__ = str(root / "inspect_binary.py")
            exec(compile(payload["inspect_binary.py"], reader.__file__, "exec"), reader.__dict__)
            report = collector.collect(app, policy, inspect_symbols=args.inspect_symbol,
                                       context_followup=True, read_range=reader.read_macho_range)
        else:
            report = collector.collect(app, policy, inspect_symbols=args.inspect_symbol)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        report["reason"] = str(error) if isinstance(error, KitError) else type(error).__name__
    report.update(identity)
    report["policySha256"] = sha(payload["deep_targets.json"])
    try:
        saved = collector.save_report(report, args.output)
        archive = saved.with_name("report.zip")
        with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as dest:
            dest.write(saved, "report.json")
            dest.write(saved.with_name("SHA256.txt"), "SHA256.txt")
        print(json.dumps({"collectionStatus": report["collectionStatus"], "buildId": identity["buildId"],
                          "reportZip": str(archive), "SYNC-001": "NOT RUN"}))
    except (OSError, ValueError, zipfile.BadZipFile):
        print("BLOCKED: REPORT_WRITE_FAILED; no successful report is claimed")
        return 2
    return 0 if report["collectionStatus"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
