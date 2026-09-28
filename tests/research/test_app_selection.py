"""Regression for the user's empty BLOCKED report; no Adobe binaries required."""
import importlib.util
from pathlib import Path
import plistlib
import subprocess
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('selection_collector', ROOT / 'research/ae-notifications/collect_app.py')
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


def fixture(root, name='Adobe After Effects.app', **metadata):
    app = root / name
    (app / 'Contents/MacOS').mkdir(parents=True)
    values = dict(CFBundleIdentifier='com.adobe.AfterEffects', CFBundleShortVersionString='25.6.0',
                  CFBundleVersion='SYNTHETIC-NOT-ADOBE', CFBundleExecutable='Test')
    values.update(metadata)
    (app / 'Contents/Info.plist').write_bytes(plistlib.dumps(values))
    (app / 'Contents/MacOS/Test').write_bytes(bytes.fromhex('cffaedfe') + b'synthetic')
    return app


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_missing_root_is_not_ambiguous_or_a_false_absence_claim(self):
        audit = {}
        with self.assertRaises(collector.DiscoveryBlocked):
            collector.discover([self.root / 'missing'], audit)
        self.assertEqual(audit['status'], 'NOT_FOUND')
        self.assertEqual(audit['roots'][0]['status'], 'MISSING')
        self.assertEqual(audit['supportedCandidateCount'], 0)

    def test_rejected_version_is_retained_not_silently_discarded(self):
        fixture(self.root, CFBundleShortVersionString='26.0')
        audit = {}
        with self.assertRaises(collector.DiscoveryBlocked):
            collector.discover([self.root], audit)
        candidate = audit['candidates'][0]
        self.assertEqual(candidate['metadata']['CFBundleShortVersionString'], '26.0')
        self.assertEqual(candidate['status'], 'REJECTED')
        self.assertIn('version', candidate['reason'])

    def test_invalid_bundle_identifier_has_its_own_reason(self):
        app = fixture(self.root, CFBundleIdentifier='not.adobe')
        details = collector.candidate_details(app)
        self.assertEqual(details['metadata']['CFBundleIdentifier'], 'not.adobe')
        self.assertIn('identifier', details['reason'])
        with self.assertRaises(collector.Blocked):
            collector.identity(app)

    def test_multiple_valid_installations_are_explicitly_ambiguous(self):
        fixture(self.root, 'Adobe After Effects one.app')
        fixture(self.root, 'Adobe After Effects two.app')
        audit = {}
        with self.assertRaises(collector.DiscoveryBlocked):
            collector.discover([self.root], audit)
        self.assertEqual(audit['status'], 'AMBIGUOUS')
        self.assertEqual(audit['supportedCandidateCount'], 2)
        self.assertEqual(len(audit['candidates']), 2)

    def test_chooser_passes_literal_unicode_space_shell_metacharacter_path(self):
        chosen = '/Applications/Тест ; $(touch bad)/Adobe After Effects.app'
        run = mock.Mock(return_value=types.SimpleNamespace(returncode=0, stdout=chosen + '\n'))
        self.assertEqual(collector.choose_app(run), Path(chosen))
        args, kwargs = run.call_args
        self.assertEqual(args[0], ['/usr/bin/osascript', '-e', collector.CHOOSE_APP_SCRIPT])
        self.assertNotIn('shell', kwargs)
        self.assertEqual(kwargs['timeout'], 180)

    def test_chooser_cancel_timeout_failure_and_invalid_path(self):
        cases = [types.SimpleNamespace(returncode=0, stdout='__FSTR_SELECTION_CANCELLED__\n'),
                 types.SimpleNamespace(returncode=0, stdout='relative.app\n'),
                 types.SimpleNamespace(returncode=0, stdout=''),
                 types.SimpleNamespace(returncode=1, stdout='')]
        for result in cases:
            with self.subTest(result=result), self.assertRaises(collector.Blocked):
                collector.choose_app(mock.Mock(return_value=result))
        with self.assertRaises(collector.Blocked):
            collector.choose_app(mock.Mock(side_effect=subprocess.TimeoutExpired('owned-chooser', 180)))

    def test_selection_cancellation_does_not_collect_or_launch_an_application(self):
        with mock.patch.object(collector, 'verify_kit', return_value={}), \
             mock.patch.object(collector.platform, 'system', return_value='Darwin'), \
             mock.patch.object(collector, 'choose_app', side_effect=collector.Blocked('cancelled')), \
             mock.patch.object(collector, 'collect') as collect, \
             mock.patch.object(collector, 'save_report', return_value=self.root / 'report.zip') as save:
            self.assertEqual(collector.main(['--choose-app']), 2)
        collect.assert_not_called()
        report = save.call_args.args[0]
        self.assertEqual(report['selection']['mode'], 'chooser')
        self.assertEqual(report['collectionStatus'], 'BLOCKED')

    def test_explicit_mismatched_app_still_retains_raw_metadata(self):
        app = fixture(self.root, CFBundleIdentifier='com.adobe.WrongFixture')
        with mock.patch.object(collector, 'verify_kit', return_value={}), \
             mock.patch.object(collector.platform, 'system', return_value='Darwin'), \
             mock.patch.object(collector, 'inspect_module') as inspect, \
             mock.patch.object(collector, 'save_report', return_value=self.root / 'report.zip') as save:
            self.assertEqual(collector.main(['--app', str(app)]), 2)
        inspect.assert_not_called()
        report = save.call_args.args[0]
        self.assertEqual(report['collectionStatus'], 'BLOCKED')
        self.assertEqual(report['selection']['candidate']['metadata']['CFBundleIdentifier'], 'com.adobe.WrongFixture')
        self.assertNotIn('modules', report)

    def test_explicit_path_does_not_invoke_discovery_or_chooser(self):
        app = fixture(self.root)
        with mock.patch.object(collector, 'verify_kit', return_value={}), \
             mock.patch.object(collector.platform, 'system', return_value='Darwin'), \
             mock.patch.object(collector, 'choose_app') as choose, \
             mock.patch.object(collector, 'discover') as discover, \
             mock.patch.object(collector, 'collect', return_value={'collectionStatus': 'PASS', 'SYNC-001': 'NOT RUN'}) as collect, \
             mock.patch.object(collector, 'save_report', return_value=self.root / 'report.zip'):
            self.assertEqual(collector.main(['--app', str(app)]), 0)
        choose.assert_not_called()
        discover.assert_not_called()
        collect.assert_called_once_with(app)

    def test_noninteractive_failure_preserves_audit_without_chooser(self):
        audit_data = {'status': 'AMBIGUOUS', 'supportedCandidateCount': 2}
        def failure(roots, audit):
            audit.update(audit_data)
            raise collector.DiscoveryBlocked('Ambiguous', audit)
        with mock.patch.object(collector, 'verify_kit', return_value={}), \
             mock.patch.object(collector.platform, 'system', return_value='Darwin'), \
             mock.patch.object(collector, 'discover', side_effect=failure), \
             mock.patch.object(collector, 'choose_app') as choose, \
             mock.patch.object(collector, 'save_report', return_value=self.root / 'report.zip') as save:
            self.assertEqual(collector.main(['--non-interactive']), 2)
        choose.assert_not_called()
        self.assertEqual(save.call_args.args[0]['selection']['discovery'], audit_data)

    def test_unrelated_app_metadata_is_not_reported(self):
        fixture(self.root, 'PrivateUnrelatedApp.app', CFBundleIdentifier='other.application')
        audit = {}
        with self.assertRaises(collector.DiscoveryBlocked):
            collector.discover([self.root], audit)
        self.assertEqual(audit['candidates'], [])

    def test_unreadable_search_is_not_reported_as_success(self):
        with mock.patch.object(collector.os, 'scandir', side_effect=PermissionError('fixture')):
            audit = {}
            with self.assertRaises(collector.DiscoveryBlocked):
                collector.discover([self.root], audit)
        self.assertEqual(audit['status'], 'INCOMPLETE')
        self.assertEqual(audit['roots'][0]['status'], 'UNREADABLE')

    def test_bad_kit_is_rejected_before_any_chooser(self):
        with mock.patch.object(collector, 'verify_kit', side_effect=ValueError('tampered')), \
             mock.patch.object(collector, 'choose_app') as choose:
            self.assertEqual(collector.main(['--choose-app']), 2)
        choose.assert_not_called()

    def test_selected_symlink_and_malformed_plist_produce_diagnostics(self):
        app = fixture(self.root)
        alias = self.root / 'alias.app'
        alias.symlink_to(app)
        self.assertEqual(collector.candidate_details(alias)['status'], 'REJECTED')
        (app / 'Contents/Info.plist').write_bytes(b'not a plist')
        details = collector.candidate_details(app)
        self.assertEqual(details['status'], 'REJECTED')
        self.assertTrue(details['errorType'])


if __name__ == '__main__':
    unittest.main()
