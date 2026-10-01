import importlib.util
import hashlib
import json
import plistlib
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MODULE=ROOT/'research/ae-notifications/chain-probe/run_disabled_start.py'
spec=importlib.util.spec_from_file_location('fstr_chain_disabled_start',MODULE)
gate=importlib.util.module_from_spec(spec); spec.loader.exec_module(gate)

class DisabledStartRunnerTests(unittest.TestCase):
    def bundle(self,root,build='fstr-chain-aegp-test-disabled',commit='a'*40,opt=False):
        bundle=Path(root)/'FSTRChainProbe.plugin'
        resources=bundle/'Contents/Resources'; resources.mkdir(parents=True)
        info={'CFBundleIdentifier':gate.BUNDLE_ID,'CFBundleName':'FSTR Chain Probe',
              'CFBundleExecutable':'FSTRChainProbe'}
        (bundle/'Contents/Info.plist').write_bytes(plistlib.dumps(info))
        receipt={'schemaVersion':1,'kind':'FSTRChainProbeResearch','sourceCommit':commit,
                 'buildId':build,'privateProbeOptIn':opt,'AEGP_load':'NOT RUN',
                 'SYNC-001':'NOT RUN','handoffApproved':False}
        (resources/'FSTRChainProbeBuild.json').write_text(json.dumps(receipt),encoding='utf-8')
        return bundle,receipt

    def test_owned_bundle_requires_exact_receipt_and_identifier(self):
        with tempfile.TemporaryDirectory() as td:
            bundle,_=self.bundle(td)
            self.assertTrue(gate.is_owned_bundle(bundle))
            info=gate.read_plist(bundle); info['CFBundleIdentifier']='other'
            (bundle/'Contents/Info.plist').write_bytes(plistlib.dumps(info))
            self.assertFalse(gate.is_owned_bundle(bundle))

    def test_bundle_file_map_is_exact_and_rejects_extra_file(self):
        with tempfile.TemporaryDirectory() as td:
            bundle,receipt=self.bundle(td)
            files={str(p.relative_to(bundle)):gate.digest(p) for p in bundle.rglob('*') if p.is_file()}
            record={'sourceCommit':receipt['sourceCommit'],'buildId':receipt['buildId'],'files':files}
            self.assertEqual(gate.verify_bundle_files(bundle,record),files)
            (bundle/'extra').write_text('x',encoding='utf-8')
            with self.assertRaisesRegex(gate.GateError,'FILE_MAP_MISMATCH'):
                gate.verify_bundle_files(bundle,record)

    def test_bundle_receipt_rejects_research_opt_in_for_disabled_install(self):
        with tempfile.TemporaryDirectory() as td:
            bundle,receipt=self.bundle(td,opt=True)
            files={str(p.relative_to(bundle)):gate.digest(p) for p in bundle.rglob('*') if p.is_file()}
            record={'sourceCommit':receipt['sourceCommit'],'buildId':receipt['buildId'],'files':files}
            with self.assertRaisesRegex(gate.GateError,'RECEIPT_MODE_MISMATCH'):
                gate.verify_bundle_files(bundle,record)

    def test_ae_process_query_uses_executable_pattern_not_broad_name(self):
        original=gate.run; captured=[]
        try:
            gate.run=lambda args,**kwargs: (captured.append(args) or SimpleNamespace(returncode=1,stdout='',stderr=''))
            with mock.patch.object(gate.platform,'system',return_value='Darwin'):
                self.assertEqual(gate.ae_pids(),[])
        finally:
            gate.run=original
        self.assertEqual(captured[0][0:2],['/usr/bin/pgrep','-f'])
        self.assertEqual(captured[0][2],gate.AE_PROCESS_PATTERN)
        self.assertIn('.app/Contents/MacOS/After Effects',gate.AE_PROCESS_PATTERN)

    def test_ae_process_pattern_matches_real_app_executable_path(self):
        sample='/Applications/Adobe After Effects 2025/Adobe After Effects 2025.app/Contents/MacOS/After Effects'
        self.assertIsNotNone(__import__('re').search(gate.AE_PROCESS_PATTERN,sample))
        malformed='/Applications/Adobe After Effects 2025/Adobe After Effects 2025Xapp/Contents/MacOS/After Effects'
        self.assertIsNone(__import__('re').search(gate.AE_PROCESS_PATTERN,malformed))

    def test_owned_cleanup_refuses_symlink_target(self):
        with tempfile.TemporaryDirectory() as td:
            original_root,original_target=gate.OWNED_ROOT,gate.TARGET
            root=Path(td)/'owned'; root.mkdir()
            elsewhere=Path(td)/'elsewhere'; elsewhere.mkdir()
            target=root/'FSTRChainProbe.plugin'; target.symlink_to(elsewhere,target_is_directory=True)
            try:
                gate.OWNED_ROOT=root; gate.TARGET=target
                with self.assertRaisesRegex(gate.GateError,'SYMLINK_REFUSED'):
                    gate.clean_owned_install()
            finally:
                gate.OWNED_ROOT=original_root; gate.TARGET=original_target

    def test_partial_install_rolls_back_owned_target_on_codesign_failure(self):
        with tempfile.TemporaryDirectory() as td:
            source_root=Path(td)/'source'; source_root.mkdir()
            bundle,receipt=self.bundle(source_root)
            files={str(p.relative_to(bundle)):gate.digest(p) for p in bundle.rglob('*') if p.is_file()}
            record={'sourceCommit':receipt['sourceCommit'],'buildId':receipt['buildId'],'files':files}
            original_root,original_target,original_run=gate.OWNED_ROOT,gate.TARGET,gate.run
            owned=Path(td)/'owned'; target=owned/'FSTRChainProbe.plugin'
            try:
                gate.OWNED_ROOT=owned; gate.TARGET=target
                gate.run=lambda *args,**kwargs: (_ for _ in ()).throw(gate.GateError('CODESIGN_FAIL'))
                with self.assertRaisesRegex(gate.GateError,'CODESIGN_FAIL'):
                    gate.install_owned(bundle,record)
                self.assertFalse(target.exists())
            finally:
                gate.OWNED_ROOT=original_root; gate.TARGET=original_target; gate.run=original_run

    def test_validate_ae_app_requires_exact_25_6_0_101(self):
        with tempfile.TemporaryDirectory(suffix='.app') as td:
            app=Path(td); mac=app/'Contents/MacOS'; mac.mkdir(parents=True)
            exe=mac/'After Effects'; exe.write_text('',encoding='utf-8')
            info={'CFBundleIdentifier':gate.AE_BUNDLE_ID,'CFBundleShortVersionString':gate.AE_SHORT_VERSION,
                  'CFBundleVersion':gate.AE_BUILD_VERSION,'CFBundleName':'Adobe After Effects 2025',
                  'CFBundleExecutable':'After Effects'}
            (app/'Contents/Info.plist').write_bytes(plistlib.dumps(info))
            found=gate.validate_ae_app(app)
            self.assertEqual(found['executable'],exe.resolve())
            info['CFBundleVersion']='25.6.0.999'
            (app/'Contents/Info.plist').write_bytes(plistlib.dumps(info))
            with self.assertRaisesRegex(gate.GateError,'IDENTITY_MISMATCH'):
                gate.validate_ae_app(app)

if __name__=='__main__':
    unittest.main()
