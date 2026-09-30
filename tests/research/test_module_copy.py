"""Actual copy launcher on owned files; never loads Adobe code or calls LLDB."""
import hashlib
import json
import os
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'research/ae-notifications/Copy-Research-Modules.command'
FILES = {'BEE.dylib': 'BEE.dylib', 'AfterFXLib': 'AfterFXLib.framework/Versions/A/AfterFXLib',
         'dvacore': 'dvacore.framework/Versions/A/dvacore'}


class ModuleCopyTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory(prefix='fstr-Юникод-')
        self.addCleanup(td.cleanup)
        self.root = Path(td.name).resolve()
        self.app = self.root / 'Owned "quoted" AE.app'
        self.out = self.root / 'outputs with spaces'
        self.paths = {}
        self.payloads = {}
        for name, relative in FILES.items():
            path = self.app / 'Contents/Frameworks' / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            data = (name.encode() + b'\x00owned fixture\n') * 100
            path.write_bytes(data)
            self.paths[name], self.payloads[name] = path, data
        (self.app / 'PRIVATE.aep').write_text('not to be copied')

    def run_copy(self, output=None):
        return subprocess.run(['bash', str(SCRIPT), '--app', str(self.app), '--output', str(output or self.out)],
                              capture_output=True, text=True, timeout=15)

    def test_copy_hashes_exact_members_originals_and_permissions(self):
        done = self.run_copy()
        self.assertEqual(done.returncode, 0, done.stderr)
        row = json.loads(done.stdout.splitlines()[0])
        path = Path(row['archive'])
        self.assertEqual(row['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
        with zipfile.ZipFile(path) as archive:
            self.assertEqual(set(archive.namelist()), set(FILES) | {'manifest.json'})
            manifest = json.loads(archive.read('manifest.json'))
            self.assertEqual(manifest['SYNC-001'], 'NOT RUN')
            self.assertEqual(manifest['copierSha256'], hashlib.sha256(SCRIPT.read_bytes()).hexdigest())
            self.assertNotIn(str(self.root), json.dumps(manifest))
            for name, data in self.payloads.items():
                self.assertEqual(archive.read(name), data)
                self.assertEqual(self.paths[name].read_bytes(), data)
                self.assertEqual(manifest['modules'][name]['sha256'], hashlib.sha256(data).hexdigest())
        self.assertEqual(path.stat().st_mode & 0o077, 0)
        self.assertEqual(path.parent.stat().st_mode & 0o077, 0)
        self.assertEqual((self.app / 'PRIVATE.aep').read_text(), 'not to be copied')

    def test_repeat_is_unique_and_does_not_overwrite(self):
        first = self.run_copy(); path = Path(json.loads(first.stdout.splitlines()[0])['archive'])
        original = path.read_bytes()
        second = self.run_copy()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertNotEqual(json.loads(second.stdout.splitlines()[0])['archive'], str(path))
        self.assertEqual(path.read_bytes(), original)

    def test_missing_input_refused_before_output(self):
        self.paths['dvacore'].unlink()
        self.assertEqual(self.run_copy().returncode, 2)
        self.assertFalse(self.out.exists())

    def test_leaf_symlink_refused(self):
        path = self.paths['BEE.dylib']; path.unlink()
        target = self.root / 'outside'; target.write_text('private')
        path.symlink_to(target)
        self.assertEqual(self.run_copy().returncode, 2)
        self.assertFalse(self.out.exists())
        self.assertEqual(target.read_text(), 'private')

    def test_directory_symlink_refused(self):
        source = self.app / 'Contents/Frameworks'; moved = self.root / 'external-frameworks'
        source.rename(moved); source.symlink_to(moved, target_is_directory=True)
        self.assertEqual(self.run_copy().returncode, 2)
        self.assertFalse(self.out.exists())

    def test_fifo_refused_without_waiting_for_writer(self):
        path = self.paths['BEE.dylib']; path.unlink(); os.mkfifo(path)
        self.assertEqual(self.run_copy().returncode, 2)
        self.assertFalse(self.out.exists())

    def test_empty_input_refused(self):
        self.paths['BEE.dylib'].write_bytes(b'')
        self.assertEqual(self.run_copy().returncode, 2)
        self.assertFalse(self.out.exists())

    def test_application_is_never_output_destination(self):
        out = self.app / 'bad-output'
        self.assertEqual(self.run_copy(out).returncode, 2)
        self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
