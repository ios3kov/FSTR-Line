"""Exact diagnostic packaging and refusal paths; no Adobe application is run."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "research/ae-notifications"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


p = load("queue_packager", ROOT / "scripts/package-queue-research.py")
k = load("queue_kit", SRC / "queue_kit.py")


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE,
                                   timeout=15).decode().strip()


def source_repo(root):
    root.mkdir()
    src = root / "research/ae-notifications"
    src.mkdir(parents=True)
    for name in p.NAMES:
        shutil.copyfile(SRC / name, src / name)
    (root / ".gitignore").write_text("dist/\n")
    git(root, "init", "-q")
    git(root, "add", ".")
    git(root, "-c", "user.name=Owned test", "-c", "user.email=test@example.invalid",
        "-c", "commit.gpgsign=false", "commit", "-qm", "owned package fixture")
    return root


class QueueKitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.repo = source_repo(self.base / 'исходники "quoted"')
        self.built = p.build(self.repo)
        self.archive = Path(self.built["archive"])
        with zipfile.ZipFile(self.archive) as archive:
            archive.extractall(self.base / "extracted")
        self.kit = self.base / "extracted/FSTR-AE-Queue"
        self.app = self.base / "Not Adobe.app"
        (self.app / "Contents").mkdir(parents=True)
        (self.app / "Contents/Info.plist").write_bytes(plistlib.dumps({"CFBundleIdentifier": "owned.fixture"}))
        self.out = self.base / "reports"

    def run_kit(self, *extra):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = k.main(["--app", str(self.app), "--output", str(self.out), *extra], root=self.kit)
        return code, stream.getvalue()

    def report(self):
        return json.loads(next(self.out.glob("*/report.json")).read_bytes())

    def test_exact_committed_payload_hashes_modes_and_identity(self):
        self.assertEqual(set(p.NAMES), set(k.FILES))
        manifest, payload = k.verify_kit(self.kit)
        self.assertEqual(manifest["sourceCommit"], git(self.repo, "rev-parse", "HEAD"))
        self.assertEqual(manifest["sourceState"], "clean")
        self.assertEqual(hashlib.sha256(self.archive.read_bytes()).hexdigest(), self.built["sha256"])
        self.assertEqual(self.archive.with_name("SHA256.txt").read_text().split()[0], self.built["sha256"])
        with zipfile.ZipFile(self.archive) as archive:
            self.assertEqual(set(archive.namelist()), {"FSTR-AE-Queue/" + n for n in (*p.NAMES, "build-manifest.json")})
            for name in p.NAMES:
                original = subprocess.check_output(["git", "-C", str(self.repo), "show",
                    manifest["sourceCommit"] + ":research/ae-notifications/" + name], timeout=15)
                self.assertEqual(payload[name], original)
                mode = archive.getinfo("FSTR-AE-Queue/" + name).external_attr >> 16
                self.assertEqual(mode, 0o100755 if name.endswith(".command") else 0o100644)
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")

    def test_bit_reproducible_from_same_commit_in_other_checkout(self):
        other = self.base / "second checkout"
        shutil.copytree(self.repo, other, ignore=shutil.ignore_patterns("dist"))
        second = p.build(other)
        self.assertEqual(second["sourceCommit"], self.built["sourceCommit"])
        self.assertEqual(Path(second["archive"]).read_bytes(), self.archive.read_bytes())

    def test_existing_output_is_not_overwritten(self):
        before = self.archive.read_bytes()
        with self.assertRaises(FileExistsError):
            p.build(self.repo)
        self.assertEqual(self.archive.read_bytes(), before)

    def test_tracked_and_untracked_dirty_source_refused(self):
        for path in (self.repo / "research/ae-notifications/queue_static.py", self.repo / "unexpected"):
            before = path.read_bytes() if path.exists() else None
            path.write_bytes(b"dirty")
            with self.assertRaisesRegex(ValueError, "DIRTY_SOURCE"):
                p.build(self.repo)
            if before is None:
                path.unlink()
            else:
                path.write_bytes(before)

    def test_missing_and_committed_symlink_source_refused(self):
        path = self.repo / "research/ae-notifications/queue_static.py"
        path.unlink()
        path.symlink_to("deep_targets.json")
        git(self.repo, "add", ".")
        git(self.repo, "-c", "user.name=Owned test", "-c", "user.email=test@example.invalid",
            "-c", "commit.gpgsign=false", "commit", "-qm", "owned symlink negative control")
        with self.assertRaisesRegex(ValueError, "NONREGULAR_SOURCE"):
            p.build(self.repo)

    def test_every_changed_payload_refused_before_code_or_collection(self):
        for name in k.FILES:
            path = self.kit / name
            before = path.read_bytes()
            path.write_bytes(before + b"\nraise AssertionError('must not execute')\n")
            code, text = self.run_kit()
            self.assertEqual(code, 2, name)
            self.assertIn("KIT_HASH_MISMATCH", text)
            self.assertFalse(self.out.exists())
            path.write_bytes(before)

    def test_missing_symlink_and_oversized_payload_refused(self):
        path = self.kit / "queue_static.py"
        before = path.read_bytes()
        path.unlink()
        self.assertEqual(self.run_kit()[0], 2)
        outside = self.base / "owned-external.py"
        outside.write_bytes(before)
        path.symlink_to(outside)
        self.assertEqual(self.run_kit()[0], 2)
        path.unlink()
        path.write_bytes(before)
        with mock.patch.object(k, "MAX_FILE", 10):
            self.assertEqual(self.run_kit()[0], 2)
        self.assertEqual(outside.read_bytes(), before)
        self.assertFalse(self.out.exists())

    def test_bad_manifest_identity_and_path_keys_refused(self):
        path = self.kit / "build-manifest.json"
        raw = path.read_bytes()
        manifest = json.loads(raw)
        bad = [None, [], {**manifest, "schemaVersion": 9}, {**manifest, "sourceState": "dirty"},
               {**manifest, "sourceCommit": "unknown"}, {**manifest, "buildId": "other"},
               {**manifest, "files": {"../escape": "a" * 64}},
               {**manifest, "files": {**manifest["files"], "queue_static.py": 10}}]
        for value in bad:
            path.write_text(json.dumps(value))
            self.assertEqual(self.run_kit()[0], 2, value)
            self.assertFalse(self.out.exists())
        path.write_bytes(raw)

    def test_verified_cli_is_isolated_from_cwd_and_pythonpath(self):
        poison = self.base / "poison"
        poison.mkdir()
        sentinel = self.base / "bad-import"
        attack = f"from pathlib import Path\nPath({str(sentinel)!r}).touch()\nraise RuntimeError('unexpected import')\n"
        (poison / "json.py").write_text(attack)
        (poison / "sitecustomize.py").write_text(attack)
        done = subprocess.run([sys.executable, "-I", "-B", str(self.kit / "queue_kit.py"), "--verify-only"],
            cwd=poison, env={**os.environ, "PYTHONPATH": str(poison)}, capture_output=True, text=True, timeout=15)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(json.loads(done.stdout)["kitStatus"], "PASS")
        self.assertFalse(sentinel.exists())
        self.assertFalse(self.out.exists())

    def test_non_macos_does_not_prompt_or_inspect(self):
        with mock.patch.object(k.platform, "system", return_value="Linux"), \
             mock.patch.object(k, "choose_application", side_effect=AssertionError("no picker")):
            self.assertEqual(self.run_kit()[0], 2)
        self.assertEqual(self.report()["reason"], "MACOS_REQUIRED")

    def test_macos_wrong_build_blocked_before_tools_and_preserves_app(self):
        original = (self.app / "Contents/Info.plist").read_bytes()
        with mock.patch.object(k.platform, "system", return_value="Darwin"), \
             mock.patch.object(subprocess, "Popen", side_effect=AssertionError("no host tools")):
            self.assertEqual(self.run_kit()[0], 2)
        self.assertEqual(self.report()["reason"], "AE_BUILD_MISMATCH")
        self.assertEqual(self.report()["commands"], [])
        self.assertEqual((self.app / "Contents/Info.plist").read_bytes(), original)

    def test_output_inside_application_refused_without_write(self):
        self.out = self.app / "do-not-create"
        for platform in ("Darwin", "Linux"):
            with mock.patch.object(k.platform, "system", return_value=platform):
                code, text = self.run_kit()
            self.assertEqual(code, 2)
            self.assertIn("OUTPUT_INSIDE_APPLICATION", text)
            self.assertFalse(self.out.exists())

    def test_independent_report_archives_have_identity_and_exact_checksum(self):
        for _ in range(2):
            self.assertEqual(self.run_kit()[0], 2)
        reports = list(self.out.glob("*/report.zip"))
        self.assertEqual(len(reports), 2)
        ids = set()
        for path in reports:
            with zipfile.ZipFile(path) as archive:
                self.assertEqual(set(archive.namelist()), {"report.json", "SHA256.txt"})
                raw = archive.read("report.json")
                self.assertEqual(hashlib.sha256(raw).hexdigest(), archive.read("SHA256.txt").decode().split()[0])
                report = json.loads(raw)
                ids.add(report["runId"])
                self.assertEqual(report["sourceCommit"], self.built["sourceCommit"])
                self.assertEqual(report["SYNC-001"], "NOT RUN")
                self.assertIs(report["privateInvocationAllowed"], False)
                self.assertEqual(report.get("commands", []), [])
        self.assertEqual(len(ids), 2)

    def test_chooser_cancel_failure_timeout(self):
        for result in (subprocess.CompletedProcess([], 0, "", ""),
                       subprocess.CompletedProcess([], 1, "", "failure")):
            with mock.patch.object(k.subprocess, "run", return_value=result), self.assertRaises(k.KitError):
                k.choose_application()
        with mock.patch.object(k.subprocess, "run", side_effect=subprocess.TimeoutExpired("owned-picker", 120)), \
             self.assertRaises(subprocess.TimeoutExpired):
            k.choose_application()

    def test_report_write_failure_is_not_success(self):
        self.out.write_bytes(b"existing owned file")
        code, text = self.run_kit()
        self.assertEqual(code, 2)
        self.assertIn("REPORT_WRITE_FAILED", text)
        self.assertEqual(self.out.read_bytes(), b"existing owned file")

    def test_shell_wrapper_verify_only(self):
        done = subprocess.run(["bash", str(self.kit / "Queue-AE.command"), "--verify-only"],
                              capture_output=True, text=True, timeout=15)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(json.loads(done.stdout)["sourceCommit"], self.built["sourceCommit"])

    @unittest.skipUnless(sys.platform == "darwin", "AppleScript syntax requires Apple tools; no interactive picker test")
    def test_real_apple_picker_compiles_without_displaying_ui(self):
        source = self.base / "picker.applescript"
        source.write_text(k.CHOOSER)
        done = subprocess.run(["/usr/bin/osacompile", "-o", str(self.base / "picker.scpt"), str(source)],
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()
