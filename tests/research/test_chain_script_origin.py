import importlib.util
import json
import plistlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[2]
MODULE=ROOT/'research/ae-notifications/chain-probe/run_script_origin.py'
spec=importlib.util.spec_from_file_location('fstr_chain_script_origin',MODULE)
gate=importlib.util.module_from_spec(spec); spec.loader.exec_module(gate)

class ScriptOriginRunnerTests(unittest.TestCase):
    def bundle(self,root,opt=True):
        bundle=Path(root)/'FSTRChainProbe.plugin'
        resources=bundle/'Contents/Resources'; resources.mkdir(parents=True)
        (bundle/'Contents/Info.plist').write_bytes(plistlib.dumps({
            'CFBundleIdentifier':gate.base.BUNDLE_ID,
            'CFBundleName':'FSTR Chain Probe',
            'CFBundleExecutable':'FSTRChainProbe',
        }))
        receipt={
            'schemaVersion':1,'kind':'FSTRChainProbeResearch','sourceCommit':'a'*40,
            'buildId':'fstr-chain-aegp-test-research-opt-in',
            'privateProbeOptIn':opt,'AEGP_load':'NOT RUN','SYNC-001':'NOT RUN',
            'handoffApproved':False,
        }
        (resources/'FSTRChainProbeBuild.json').write_text(json.dumps(receipt),encoding='utf-8')
        files={str(p.relative_to(bundle)):gate.base.digest(p)
               for p in bundle.rglob('*') if p.is_file()}
        record={'sourceCommit':receipt['sourceCommit'],'buildId':receipt['buildId'],'files':files}
        return bundle,record

    def test_applescript_quote_escapes_script_text(self):
        quoted=gate.applescript_quote('a"b\\c')
        self.assertEqual(quoted,'"a\\"b\\\\c"')

    def test_active_bundle_requires_research_opt_in_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            bundle,record=self.bundle(td,opt=True)
            self.assertEqual(gate.verify_active_bundle(bundle,record),record['files'])
        with tempfile.TemporaryDirectory() as td:
            bundle,record=self.bundle(td,opt=False)
            with self.assertRaisesRegex(gate.GateError,'RECEIPT_MODE_MISMATCH'):
                gate.verify_active_bundle(bundle,record)

    def test_do_script_uses_documented_applescript_command(self):
        original=gate.base.run; calls=[]
        try:
            gate.base.run=lambda args,**kwargs: (calls.append(args) or SimpleNamespace(stdout='OK\n'))
            self.assertEqual(gate.do_script('Adobe After Effects 2025','1+1;'),'OK')
        finally:
            gate.base.run=original
        self.assertEqual(calls[0][0:2],['/usr/bin/osascript','-e'])
        self.assertIn('DoScript "1+1;"',calls[0][2])
        self.assertIn('tell application "Adobe After Effects 2025"',calls[0][2])

    def test_project_preflight_blocks_unproven_empty_state(self):
        original=gate.do_script
        try:
            gate.do_script=lambda *args,**kwargs:'NOT_EMPTY'
            with self.assertRaisesRegex(gate.GateError,'PROJECT_NOT_PROVEN_EMPTY'):
                gate.require_empty_unsaved_project('AE')
        finally:
            gate.do_script=original

    def test_owned_project_cleanup_checks_identity_before_close(self):
        original=gate.do_script; scripts=[]
        try:
            gate.do_script=lambda app,script,**kwargs: (
                scripts.append(script) or 'FSTR_OWNED_PROJECT_CLOSED')
            gate.require_owned_project_and_close('AE')
        finally:
            gate.do_script=original
        self.assertIn('app.project.file!==null',scripts[0])
        self.assertIn('app.project.numItems!==1',scripts[0])
        self.assertIn('FSTR Chain Probe Test',scripts[0])
        self.assertIn('FSTR Probe Layer',scripts[0])
        self.assertIn('CloseOptions.DO_NOT_SAVE_CHANGES',scripts[0])

if __name__=='__main__':
    unittest.main()
