import importlib.util
from contextlib import ExitStack
import json
import plistlib
import tempfile
import sys
import unittest
from unittest import mock
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

    def test_fraction_pair_reduces_decimal_time(self):
        self.assertEqual(gate.fraction_pair('1.5'),[3,2])
        self.assertEqual(gate.fraction_pair('2'),[2,1])

    def test_edit_command_ids_are_resolved_before_dynamic_undo_labels(self):
        original=gate.do_script; scripts=[]
        try:
            gate.do_script=lambda app,script,**kwargs: (
                scripts.append(script) or 'FSTR_EDIT_COMMAND_IDS:16|2035')
            ids=gate.resolve_edit_command_ids('AE')
        finally:
            gate.do_script=original
        self.assertEqual(ids,{'Undo':16,'Redo':2035})
        self.assertIn('findMenuCommandId("Undo")',scripts[0])
        self.assertIn('findMenuCommandId("Redo")',scripts[0])

    def test_edit_command_id_resolution_fails_closed(self):
        original=gate.do_script
        try:
            for result in ('NO_IDS','FSTR_EDIT_COMMAND_IDS:0|2035',
                           'FSTR_EDIT_COMMAND_IDS:16|16','FSTR_EDIT_COMMAND_IDS:x|17'):
                gate.do_script=lambda *args,_result=result,**kwargs:_result
                with self.assertRaises(gate.GateError):
                    gate.resolve_edit_command_ids('AE')
        finally:
            gate.do_script=original

    def test_execute_command_uses_pre_resolved_numeric_id(self):
        original=gate.do_script; scripts=[]
        try:
            gate.do_script=lambda app,script,**kwargs: (
                scripts.append(script) or 'FSTR_COMMAND:Undo')
            gate.execute_command_id('AE',16,'Undo')
        finally:
            gate.do_script=original
        self.assertIn('app.executeCommand(16)',scripts[0])
        self.assertNotIn('findMenuCommandId',scripts[0])

    def test_script_edit_uses_one_explicit_undo_group_per_call(self):
        original=gate.do_script; scripts=[]
        try:
            gate.do_script=lambda app,script,**kwargs: (
                scripts.append(script) or 'FSTR_START_TIME:1')
            gate.set_start_time('AE',1.0)
            gate.set_start_time('AE',2.0)
        finally:
            gate.do_script=original
        self.assertEqual(len(scripts),2)
        for script in scripts:
            self.assertEqual(script.count('app.beginUndoGroup('),1)
            self.assertEqual(script.count('app.endUndoGroup()'),1)
            self.assertLess(script.index('app.beginUndoGroup('),script.index('l.startTime='))
            self.assertLess(script.index('l.startTime='),script.index('app.endUndoGroup()'))
            self.assertIn('try{',script)
            self.assertIn('}finally{app.endUndoGroup();}',script)

    def test_read_layer_state_returns_public_ground_truth(self):
        original=gate.do_script
        try:
            gate.do_script=lambda *args,**kwargs:'FSTR_LAYER_STATE:12|1.5|2|8'
            state=gate.read_layer_state('AE','undo')
        finally:
            gate.do_script=original
        self.assertEqual(state,{'label':'undo','id':12,'offset':[3,2],
                                'in':[2,1],'duration':[8,1]})

    def test_read_layer_state_rejects_malformed_result(self):
        original=gate.do_script
        try:
            gate.do_script=lambda *args,**kwargs:'FSTR_LAYER_STATE:12|1|2'
            with self.assertRaisesRegex(gate.GateError,'LAYER_STATE_FORMAT_INVALID'):
                gate.read_layer_state('AE','edit')
        finally:
            gate.do_script=original

    def test_observed_phase_waits_for_callback_before_public_read(self):
        order=[]
        action=lambda: order.append('action')
        with mock.patch.object(gate,'observation_count',side_effect=lambda *args: (order.append('count') or 4)), \
             mock.patch.object(gate,'wait_for_new_observation',side_effect=lambda *args,**kwargs: (order.append('wait') or 5)), \
             mock.patch.object(gate,'read_layer_state',side_effect=lambda *args,**kwargs: (order.append('read') or {
                 'label':'edit','id':12,'offset':[1,1],'in':[1,1],'duration':[10,1]})):
            phase,state=gate.run_observed_phase('AE','trace','build',2,12,'edit',action)
        self.assertEqual(order,['count','action','wait','read'])
        self.assertEqual(phase['observationsBefore'],4)
        self.assertEqual(phase['observationsAfter'],5)
        self.assertEqual(state['id'],12)

    def test_project_preflight_blocks_unproven_empty_state(self):
        original=gate.do_script
        try:
            gate.do_script=lambda *args,**kwargs:'NOT_EMPTY'
            with self.assertRaisesRegex(gate.GateError,'PROJECT_NOT_PROVEN_EMPTY'):
                gate.require_empty_unsaved_project('AE')
        finally:
            gate.do_script=original

    def test_project_preflight_blocks_when_query_itself_fails(self):
        original=gate.do_script
        try:
            gate.do_script=lambda *args,**kwargs: (_ for _ in ()).throw(gate.base.GateError('COMMAND_FAILED'))
            with self.assertRaisesRegex(gate.GateError,'BLOCKED_PROJECT_NOT_PROVEN_EMPTY'):
                gate.require_empty_unsaved_project('AE')
        finally:
            gate.do_script=original

    def test_partial_project_creation_failure_does_not_quit_or_remove_loaded_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            bundle=root/'FSTRChainProbe.plugin'; bundle.mkdir()
            record_path=root/'build-record.json'; record_path.write_text('{}',encoding='utf-8')
            trace_path=root/'trace.jsonl'; trace_path.write_text('{}\n',encoding='utf-8')
            record={'sourceCommit':'a'*40,'buildId':'fstr-test','files':{}}
            clean=mock.Mock()
            quit_ae=mock.Mock()
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(sys,'argv',['run_script_origin.py','--sdk',str(root/'sdk')]))
                stack.enter_context(mock.patch.object(gate.base.platform,'system',return_value='Darwin'))
                stack.enter_context(mock.patch.object(gate.base.platform,'machine',return_value='arm64'))
                stack.enter_context(mock.patch.object(gate.base,'ae_pids',return_value=[]))
                stack.enter_context(mock.patch.object(gate.base,'discover_ae_app',return_value={'path':root/'AE.app','name':'AE'}))
                stack.enter_context(mock.patch.object(gate.base,'clean_owned_install',clean))
                stack.enter_context(mock.patch.object(gate.base,'refuse_conflicting_copies'))
                stack.enter_context(mock.patch.object(gate,'build_active',return_value=(bundle,record,record_path)))
                stack.enter_context(mock.patch.object(gate,'verify_active_bundle'))
                stack.enter_context(mock.patch.object(gate,'install_active'))
                stack.enter_context(mock.patch.object(gate.base,'digest',return_value='hash'))
                stack.enter_context(mock.patch.object(gate.base,'launch_ae'))
                stack.enter_context(mock.patch.object(gate.base,'wait_for_ae'))
                stack.enter_context(mock.patch.object(gate.base,'new_trace',return_value=trace_path))
                stack.enter_context(mock.patch.object(gate.base,'trace_ready'))
                stack.enter_context(mock.patch.object(gate,'require_empty_unsaved_project'))
                stack.enter_context(mock.patch.object(gate,'create_owned_test_project',side_effect=gate.GateError('CREATE_FAIL')))
                stack.enter_context(mock.patch.object(gate.base,'cleanup_ae_running',return_value=True))
                stack.enter_context(mock.patch.object(gate.base,'request_quit',quit_ae))
                stack.enter_context(mock.patch.object(gate,'write_evidence',return_value=root/'evidence.json'))
                with self.assertRaisesRegex(gate.GateError,'CREATE_FAIL'):
                    gate.main()
            self.assertEqual(clean.call_count,1)
            quit_ae.assert_not_called()

    def test_active_probe_failure_never_quits_if_stop_outcome_becomes_unknown(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            bundle=root/'FSTRChainProbe.plugin'; bundle.mkdir()
            record_path=root/'build-record.json'; record_path.write_text('{}',encoding='utf-8')
            trace_path=root/'trace.jsonl'; trace_path.write_text('{}\n',encoding='utf-8')
            record={'sourceCommit':'a'*40,'buildId':'fstr-test','files':{}}
            clean=mock.Mock()
            quit_ae=mock.Mock()
            close_owned=mock.Mock()
            toggle=mock.Mock(side_effect=['STARTED',gate.GateError('STOP_FAIL')])
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(sys,'argv',['run_script_origin.py','--sdk',str(root/'sdk')]))
                stack.enter_context(mock.patch.object(gate.base.platform,'system',return_value='Darwin'))
                stack.enter_context(mock.patch.object(gate.base.platform,'machine',return_value='arm64'))
                stack.enter_context(mock.patch.object(gate.base,'ae_pids',return_value=[]))
                stack.enter_context(mock.patch.object(gate.base,'discover_ae_app',return_value={'path':root/'AE.app','name':'AE'}))
                stack.enter_context(mock.patch.object(gate.base,'clean_owned_install',clean))
                stack.enter_context(mock.patch.object(gate.base,'refuse_conflicting_copies'))
                stack.enter_context(mock.patch.object(gate,'build_active',return_value=(bundle,record,record_path)))
                stack.enter_context(mock.patch.object(gate,'verify_active_bundle'))
                stack.enter_context(mock.patch.object(gate,'install_active'))
                stack.enter_context(mock.patch.object(gate.base,'digest',return_value='hash'))
                stack.enter_context(mock.patch.object(gate.base,'launch_ae'))
                stack.enter_context(mock.patch.object(gate.base,'wait_for_ae'))
                stack.enter_context(mock.patch.object(gate.base,'new_trace',return_value=trace_path))
                stack.enter_context(mock.patch.object(gate.base,'trace_ready'))
                stack.enter_context(mock.patch.object(gate,'require_empty_unsaved_project'))
                stack.enter_context(mock.patch.object(gate,'create_owned_test_project',return_value=12))
                stack.enter_context(mock.patch.object(gate,'toggle_probe',toggle))
                stack.enter_context(mock.patch.object(gate,'wait_for_prefix',return_value=[]))
                stack.enter_context(mock.patch.object(gate,'observation_count',return_value=0))
                stack.enter_context(mock.patch.object(gate,'set_start_time',side_effect=gate.GateError('EDIT_FAIL')))
                stack.enter_context(mock.patch.object(gate,'require_owned_project_and_close',close_owned))
                stack.enter_context(mock.patch.object(gate.base,'cleanup_ae_running',return_value=True))
                stack.enter_context(mock.patch.object(gate.base,'request_quit',quit_ae))
                stack.enter_context(mock.patch.object(gate,'write_evidence',return_value=root/'evidence.json'))
                with self.assertRaisesRegex(gate.GateError,'EDIT_FAIL'):
                    gate.main()
            self.assertEqual(toggle.call_count,2)
            self.assertEqual(clean.call_count,1)
            close_owned.assert_not_called()
            quit_ae.assert_not_called()

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
