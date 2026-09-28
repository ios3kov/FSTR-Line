import hashlib
import importlib.util
import json
from pathlib import Path
import plistlib
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('collect_app', ROOT / 'research/ae-notifications/collect_app.py')
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


def fixture(root, name='AE.app', **overrides):
    app = root / name
    (app / 'Contents/MacOS').mkdir(parents=True)
    values = dict(CFBundleIdentifier='com.adobe.AfterEffects.application', CFBundleShortVersionString='25.6.0',
                  CFBundleVersion='fixture-not-Adobe', CFBundleExecutable='AEFixture')
    values.update(overrides)
    (app / 'Contents/Info.plist').write_bytes(plistlib.dumps(values))
    (app / 'Contents/MacOS/AEFixture').write_bytes(bytes.fromhex('cffaedfe') + b'fixture bytes')
    return app


def fake_inspect(path, output, timeout):
    return {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'stringScanLimited': False,
            'slices': [{'uuid': 'fixture', 'symbolsLimited': False}], 'notificationSource': 'NOT RUN'}


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.app = fixture(self.root)

    def tearDown(self):
        self.directory.cleanup()

    def test_metadata_not_runtime_acceptance(self):
        _, binary, meta = collector.identity(self.app)
        self.assertEqual(binary.name, 'AEFixture')
        self.assertFalse(meta['runtimeIdentityVerified'])
        self.assertFalse(meta['exactBuild101Verified'])

    def test_reject_other_version_without_scanning(self):
        app = fixture(self.root, 'Wrong.app', CFBundleShortVersionString='26.0')
        with self.assertRaises(collector.Blocked):
            collector.collect(app, inspector=lambda *args: self.fail('No scan expected'))

    def test_executable_path_traversal(self):
        app = fixture(self.root, 'Traversal.app', CFBundleExecutable='../../../outside')
        with self.assertRaises(ValueError):
            collector.identity(app)

    def test_main_symlink_rejected(self):
        binary = self.app / 'Contents/MacOS/AEFixture'
        binary.unlink()
        binary.symlink_to(self.root / 'outside')
        with self.assertRaises(ValueError):
            collector.identity(self.app)

    def test_internal_links_do_not_escape_and_sample_project_not_read(self):
        links = self.app / 'Contents/links'
        links.symlink_to(self.root, target_is_directory=True)
        project = self.app / 'Contents/never.aep'
        project.write_bytes(bytes.fromhex('cffaedfe') + b'not a module')
        result = collector.collect(self.app, inspector=fake_inspect)
        self.assertEqual(len(result['modules']), 1)
        self.assertEqual(result['collectionStatus'], 'PASS')

    def test_main_first_framework_real_file_included(self):
        module = self.app / 'Contents/Frameworks/A.framework/Versions/A/A'
        module.parent.mkdir(parents=True)
        module.write_bytes(bytes.fromhex('cffaedfe') + b'other')
        alias = self.app / 'Contents/Frameworks/A.framework/A'
        alias.symlink_to('Versions/A/A')
        result = collector.collect(self.app, inspector=fake_inspect)
        self.assertEqual([item['relativePath'] for item in result['modules']],
                         ['Contents/MacOS/AEFixture', 'Contents/Frameworks/A.framework/Versions/A/A'])

    def test_no_modification_of_inputs(self):
        before = {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.app.rglob('*') if p.is_file()}
        result = collector.collect(self.app, inspector=fake_inspect)
        after = {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.app.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(result['SYNC-001'], 'NOT RUN')
        self.assertIsNone(result['notificationCandidate'])

    def test_byte_limit_cannot_be_pass(self):
        result = collector.collect(self.app, inspector=fake_inspect, max_bytes=1)
        self.assertEqual(result['collectionStatus'], 'BLOCKED')
        self.assertEqual(result['modules'], [])

    def test_module_limit_cannot_hide_partial_scan(self):
        (self.app / 'Contents/another').write_bytes(bytes.fromhex('cffaedfe') + b'data')
        result = collector.collect(self.app, inspector=fake_inspect, max_modules=1)
        self.assertEqual(result['collectionStatus'], 'BLOCKED')
        self.assertEqual(len(result['modules']), 1)

    def test_worker_timeout_reported_and_other_modules_continue(self):
        def timeout(*args):
            raise subprocess.TimeoutExpired('owned-worker', 1)
        result = collector.collect(self.app, inspector=timeout)
        self.assertEqual(result['collectionStatus'], 'BLOCKED')
        self.assertEqual(result['modules'][0]['status'], 'BLOCKED')

    def test_bad_module_never_silently_dropped(self):
        def fail(*args):
            raise ValueError('bad binary')
        result = collector.collect(self.app, inspector=fail)
        self.assertEqual(result['collectionStatus'], 'FAIL')
        self.assertEqual(result['modules'][0]['status'], 'FAIL')

    def test_module_mutation_is_detected(self):
        def change(path, *args):
            result = fake_inspect(path, *args)
            path.write_bytes(path.read_bytes() + b'update')
            return result
        result = collector.collect(self.app, inspector=change)
        self.assertEqual(result['collectionStatus'], 'FAIL')

    def test_discovery_unique_then_ambiguous(self):
        self.assertEqual(collector.discover([self.root]), self.app.resolve())
        fixture(self.root, 'Another.app')
        with self.assertRaises(collector.Blocked):
            collector.discover([self.root])

    def test_nested_adobe_installation(self):
        nested = self.root / 'Adobe After Effects 2025'
        nested.mkdir()
        app = fixture(nested)
        self.assertEqual(collector.discover([nested]), app.resolve())

    def test_zip_contains_only_redacted_json_and_unique_identity(self):
        report = {'collectionStatus': 'PASS', 'SYNC-001': 'NOT RUN', 'context': '/Users/alice/file user@example.org'}
        a = collector.save_report(report, self.root / 'results', {})
        b = collector.save_report(report, self.root / 'results', {})
        self.assertNotEqual(a, b)
        with zipfile.ZipFile(a) as archive:
            self.assertEqual(archive.namelist(), ['report.json'])
            raw = archive.read('report.json').decode()
            self.assertNotIn('alice', raw)
            self.assertNotIn('user@example.org', raw)
            self.assertIn('[user]', raw)
        expected = hashlib.sha256(a.read_bytes()).hexdigest()
        self.assertTrue(Path(str(a) + '.sha256').read_text().startswith(expected))

    def test_kit_manifest_tamper_rejected(self):
        kit = self.root / 'kit'
        kit.mkdir()
        files = {}
        for name in collector.TOOLS:
            (kit / name).write_text('fixture')
            files[name] = hashlib.sha256(b'fixture').hexdigest()
        (kit / 'build-manifest.json').write_text(json.dumps(dict(sourceCommit='a' * 40, sourceState='clean', files=files)))
        self.assertEqual(collector.verify_kit(kit)['sourceState'], 'clean')
        (kit / 'inspect_binary.py').write_text('tampered')
        with self.assertRaises(ValueError):
            collector.verify_kit(kit)


if __name__ == '__main__':
    unittest.main()
