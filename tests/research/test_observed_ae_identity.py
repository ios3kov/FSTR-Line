"""Independent metadata regression from the supplied report; no Adobe executable."""
import importlib.util
import json
from pathlib import Path
import plistlib
import struct
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('observed_ae_collector', ROOT / 'research/ae-notifications/collect_app.py')
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)
OBSERVED = json.loads((Path(__file__).parent / 'fixtures/ae-25.6-observed-metadata.json').read_text())


class ObservedIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.app = self.root / OBSERVED['appName']
        (self.app / 'Contents/MacOS').mkdir(parents=True)
        self.metadata = dict(OBSERVED['metadata'])
        self.write_metadata()
        self.binary = self.app / 'Contents/MacOS' / self.metadata['CFBundleExecutable']
        # Minimal synthetic Mach-O header, not bytes from Adobe.
        self.binary.write_bytes(struct.pack('<8I', 0xFEEDFACF, 0x100000C, 0, 2, 0, 0, 0, 0))

    def tearDown(self):
        self.temp.cleanup()

    def write_metadata(self):
        (self.app / 'Contents/Info.plist').write_bytes(plistlib.dumps(self.metadata))

    def test_exact_observed_tuple_passes_identity(self):
        _, binary, meta = collector.identity(self.app)
        self.assertEqual(binary.name, 'After Effects')
        self.assertEqual(meta['bundleId'], OBSERVED['metadata']['CFBundleIdentifier'])
        self.assertEqual(meta['shortVersion'], '25.6.0')
        self.assertEqual(meta['bundleVersion'], '25.6.0.101')
        self.assertFalse(meta['runtimeIdentityVerified'])
        self.assertFalse(meta['exactBuild101Verified'])

    def test_auto_discovery_accepts_the_observed_application(self):
        audit = {}
        self.assertEqual(collector.discover([self.root], audit), self.app.resolve())
        self.assertEqual(audit['status'], 'FOUND')
        self.assertEqual(audit['supportedCandidateCount'], 1)
        self.assertEqual(audit['candidates'][0]['metadata'], OBSERVED['metadata'])

    def test_real_inspector_child_receives_the_observed_executable_name(self):
        before = self.binary.read_bytes()
        report = collector.collect(self.app)
        self.assertEqual(report['collectionStatus'], 'PASS')
        self.assertEqual(report['modules'][0]['relativePath'], 'Contents/MacOS/After Effects')
        self.assertEqual(report['modules'][0]['status'], 'PASS')
        self.assertEqual(report['modules'][0]['inspection']['staticInspection'], 'PASS')
        self.assertEqual(report['SYNC-001'], 'NOT RUN')
        self.assertIsNone(report['notificationCandidate'])
        self.assertEqual(self.binary.read_bytes(), before)

    def test_previous_invented_id_and_lookalike_ids_are_rejected(self):
        for bad in ('com.adobe.AfterEffects', 'com.adobe.AfterEffects.application.evil',
                    'com.adobe.AfterEffects.applicationX', 'COM.ADOBE.AfterEffects.application'):
            with self.subTest(bundle=bad):
                self.metadata['CFBundleIdentifier'] = bad
                self.write_metadata()
                with self.assertRaises(collector.Blocked):
                    collector.identity(self.app)

    def test_correct_id_does_not_bypass_version_checks(self):
        for bad in ('25.5.0', '26.0', '125.6.0', '25.60', ''):
            with self.subTest(version=bad):
                self.metadata['CFBundleShortVersionString'] = bad
                self.write_metadata()
                with self.assertRaises(collector.Blocked):
                    collector.identity(self.app)

    def test_correct_metadata_does_not_bypass_binary_check(self):
        self.binary.write_bytes(b'not a Mach-O executable')
        with self.assertRaises(ValueError):
            collector.identity(self.app)

    def test_correct_metadata_does_not_bypass_symlink_check(self):
        alias = self.root / 'Alias.app'
        alias.symlink_to(self.app, target_is_directory=True)
        with self.assertRaises(ValueError):
            collector.identity(alias)


if __name__ == '__main__':
    unittest.main()
