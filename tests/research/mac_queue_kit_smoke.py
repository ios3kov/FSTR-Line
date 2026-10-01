#!/usr/bin/env python3
"""Exercise the exact CI ZIP, not a rebuilt lookalike. No Adobe process or UI."""
import hashlib
import json
import plistlib
import subprocess
import sys
import tempfile
import types
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAMES = {"Queue-AE.command", "queue_kit.py", "queue_static.py", "deep_targets.json", "QUEUE-README.txt", "build-manifest.json",
         "inspect_binary.py", "Queue-Context.command", "Queue-Details.command"}


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
        def run(*args, entry="Queue-AE.command"):
            return subprocess.run(["bash", str(kit / entry), *args],
                                  capture_output=True, text=True, timeout=30)
        for entry in ("Queue-AE.command", "Queue-Context.command", "Queue-Details.command"):
            checked = run("--verify-only", entry=entry)
            assert checked.returncode == 0, checked.stdout + checked.stderr
            assert json.loads(checked.stdout)["sourceCommit"] == commit
        app = work / "Owned non Adobe.app"
        (app / "Contents").mkdir(parents=True)
        metadata = plistlib.dumps({"CFBundleIdentifier": "org.fstr.owned-fixture"})
        (app / "Contents/Info.plist").write_bytes(metadata)
        for entry in ("Queue-AE.command", "Queue-Context.command", "Queue-Details.command"):
            out = work / ("reports-" + entry)
            refused = run("--app", str(app), "--output", str(out), entry=entry)
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
        # Exercise the exact packaged reader on a genuine linked, owned arm64 image.
        reader = types.ModuleType("owned_packaged_range_reader")
        reader.__file__ = str(kit / "inspect_binary.py")
        exec(compile((kit / "inspect_binary.py").read_bytes(), reader.__file__, "exec"), reader.__dict__)
        source = work / "owned.c"
        source.write_text("const unsigned char fstr_range_table[4]={1,7,29,43};\nint fstr_range_control(void){return 1;}\n")
        binary = work / "owned.dylib"
        subprocess.run(["xcrun", "clang", "-arch", "arm64", "-dynamiclib", str(source), "-o", str(binary)],
                       check=True, capture_output=True, timeout=30)
        symbols = subprocess.check_output(["xcrun", "nm", "-U", str(binary)], text=True, timeout=30)
        line = next(line for line in symbols.splitlines() if line.split() and line.split()[-1] == "_fstr_range_table")
        address = int(line.split()[0], 16)
        image = next(s for s in reader.parse_macho(binary.read_bytes()) if s["cpuType"] == 0x100000c)
        table = reader.read_macho_range(binary, hashlib.sha256(binary.read_bytes()).hexdigest(), image["uuid"], address, 4)
        assert table["hex"] == "01071d2b" and table["byteCount"] == 4, table
        # The actual packaged collector, with test-only image identity; no Adobe.
        from test_queue_context_details import linked_details_control
        collector = types.ModuleType("owned_packaged_details_collector")
        collector.__file__ = str(kit / "queue_static.py")
        exec(compile((kit / "queue_static.py").read_bytes(), collector.__file__, "exec"), collector.__dict__)
        details = linked_details_control(collector, work / "details-owned")
        assert details["collectionStatus"] == "PASS" and details["expectedBodyCount"] == 8, details
    evidence = {"status": "PASS", "sourceCommit": commit, "kitSha256": digest,
                "scope": "Exact CI ZIP launchers, integrity, wrong-app refusal and owned Mach-O range; NOT Adobe AE",
                "contextLauncher": "PASS", "detailsLauncher": "PASS", "ownedLinkedDetailsProfile": "PASS",
                "detailsBodyCount": 8, "ownedLinkedMachoRange": "PASS",
                "actualAE": "NOT RUN", "interactivePicker": "NOT RUN", "SYNC-001": "NOT RUN"}
    target = ROOT / "dist/notification-evidence/queue-kit.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence))


if __name__ == "__main__":
    main()
