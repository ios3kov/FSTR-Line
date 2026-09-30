#!/usr/bin/env python3
"""Exercise the exact CI ZIP, not a rebuilt lookalike. No Adobe process or UI."""
import hashlib
import json
import plistlib
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAMES = {"Queue-AE.command", "queue_kit.py", "queue_static.py", "deep_targets.json", "QUEUE-README.txt", "build-manifest.json"}


def main():
    if sys.platform != "darwin":
        raise SystemExit("BLOCKED: this exact-kit smoke requires macOS")
    commit = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True, timeout=15).strip()
    archive = ROOT / "dist/queue-research" / commit / "FSTR-AE-Queue.zip"
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert archive.with_name("SHA256.txt").read_text().split()[0] == digest
    with tempfile.TemporaryDirectory(prefix="fstr-queue-kit-") as td:
        work = Path(td).resolve()
        kit = work / "Extracted kit"
        kit.mkdir()
        with zipfile.ZipFile(archive) as src:
            assert set(src.namelist()) == {"FSTR-AE-Queue/" + n for n in NAMES}
            for name in NAMES:
                (kit / name).write_bytes(src.read("FSTR-AE-Queue/" + name))
        def run(*args):
            return subprocess.run(["bash", str(kit / "Queue-AE.command"), *args],
                                  capture_output=True, text=True, timeout=30)
        checked = run("--verify-only")
        assert checked.returncode == 0, checked.stdout + checked.stderr
        assert json.loads(checked.stdout)["sourceCommit"] == commit
        app = work / "Owned non Adobe.app"
        (app / "Contents").mkdir(parents=True)
        metadata = plistlib.dumps({"CFBundleIdentifier": "org.fstr.owned-fixture"})
        (app / "Contents/Info.plist").write_bytes(metadata)
        out = work / "reports"
        refused = run("--app", str(app), "--output", str(out))
        assert refused.returncode == 2, refused.stdout + refused.stderr
        result = json.loads(refused.stdout)
        report_zip = Path(result["reportZip"])
        assert report_zip.resolve().is_relative_to(out)
        with zipfile.ZipFile(report_zip) as src:
            assert set(src.namelist()) == {"report.json", "SHA256.txt"}
            raw = src.read("report.json")
            assert hashlib.sha256(raw).hexdigest() == src.read("SHA256.txt").decode().split()[0]
        report = json.loads(raw)
        assert report["reason"] == "AE_BUILD_MISMATCH", report
        assert report["sourceCommit"] == commit and report["commands"] == []
        assert report["SYNC-001"] == "NOT RUN" and report["privateInvocationAllowed"] is False
        assert (app / "Contents/Info.plist").read_bytes() == metadata
        assert len(list(app.rglob("*"))) == 2
    evidence = {"status": "PASS", "sourceCommit": commit, "kitSha256": digest,
                "scope": "Exact CI ZIP launcher, integrity and wrong-app refusal on owned fixture; NOT Adobe AE",
                "actualAE": "NOT RUN", "interactivePicker": "NOT RUN", "SYNC-001": "NOT RUN"}
    target = ROOT / "dist/notification-evidence/queue-kit.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence))


if __name__ == "__main__":
    main()
