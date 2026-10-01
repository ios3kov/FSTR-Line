import importlib.util
import hashlib
import json
import plistlib
import tempfile
import unittest
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

    def test_validate_ae_app_requires_exact_25_6_0_101(self):
        with tempfile.TemporaryDirectory(suffix='.app') as td:
            app=Path(td); mac=app/'Contents/MacOS'; mac.mkdir(parents=True)
            exe=mac/'After Effects'; exe.write_text('',encoding='utf-8')
            info={'CFBundleIdentifier':gate.AE_BUNDLE_ID,'CFBundleShortVersionString':gate.AE_SHORT_VERSION,
                  'CFBundleVersion':gate.AE_BUILD_VERSION,'CFBundleName':'Adobe After Effects 2025',
                  'CFBundleExecutable':'After Effects'}
            (app/'Contents/Info.plist').write_bytes(plistlib.dumps(info))
            found=gate.validate_ae_app(app)
            self.assertEqual(found['executable'],exe)
            info['CFBundleVersion']='25.6.0.999'
            (app/'Contents/Info.plist').write_bytes(plistlib.dumps(info))
            with self.assertRaisesRegex(gate.GateError,'IDENTITY_MISMATCH'):
                gate.validate_ae_app(app)

if __name__=='__main__':
    unittest.main()
