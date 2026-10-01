import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MODULE=ROOT/'research/ae-notifications/chain-probe/run_native_gates.py'
spec=importlib.util.spec_from_file_location('fstr_chain_native_gates',MODULE)
gate=importlib.util.module_from_spec(spec); spec.loader.exec_module(gate)

class NativeGateOrchestratorTests(unittest.TestCase):
    def stage(self,status='PASS',commit='a'*40,kind='FSTRChainProbeDisabledStart',
              build='build',ae='25.6.0.101'):
        row={'kind':kind,'status':status,'evidence':'dist/evidence.json','sha256':'f'*64,
             'AEGP_load':'OBSERVED' if status=='PASS' else 'NOT RUN',
             'SYNC-001':'NOT RUN'}
        if status=='PASS':
            row.update({'sourceCommit':commit,'buildId':build,'aeVersion':ae})
        return row

    def test_disabled_failure_stops_before_active_stage(self):
        calls=[]
        def runner(stage,*args):
            calls.append(stage)
            return self.stage(status='BLOCKED')
        result=gate.orchestrate('/sdk',runner=runner)
        self.assertEqual(calls,['disabled'])
        self.assertEqual(result['status'],'BLOCKED')
        self.assertEqual(result['stoppedAfter'],'disabled')

    def test_active_failure_stops_after_second_stage(self):
        calls=[]
        def runner(stage,*args):
            calls.append(stage)
            if stage=='disabled':
                return self.stage()
            return self.stage(status='FAIL',kind='FSTRChainProbeScriptOrigin')
        result=gate.orchestrate('/sdk',runner=runner)
        self.assertEqual(calls,['disabled','script-origin'])
        self.assertEqual(result['status'],'FAIL')
        self.assertEqual(result['stoppedAfter'],'script-origin')

    def test_pass_requires_same_commit_and_ae_version(self):
        disabled=self.stage()
        active=self.stage(kind='FSTRChainProbeScriptOrigin',build='active')
        result=gate.orchestrate('/sdk',runner=lambda stage,*args: disabled if stage=='disabled' else active)
        self.assertEqual(result['status'],'PASS')
        self.assertEqual(result['sourceCommit'],'a'*40)
        self.assertEqual(result['SYNC-001'],'PARTIAL_SCRIPT_ORIGIN_RUNTIME_EVIDENCE_ONLY')
        bad_commit=self.stage(commit='b'*40,kind='FSTRChainProbeScriptOrigin',build='active')
        with self.assertRaisesRegex(gate.GateError,'SOURCE_COMMIT_MISMATCH'):
            gate.orchestrate('/sdk',runner=lambda stage,*args: disabled if stage=='disabled' else bad_commit)
        bad_ae=self.stage(kind='FSTRChainProbeScriptOrigin',build='active',ae='25.6.0.999')
        with self.assertRaisesRegex(gate.GateError,'AE_VERSION_MISMATCH'):
            gate.orchestrate('/sdk',runner=lambda stage,*args: disabled if stage=='disabled' else bad_ae)

    def test_child_evidence_is_scoped_and_identified(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); run=root/'child'; run.mkdir()
            path=run/'disabled-start.json'
            row={'schemaVersion':1,'kind':'FSTRChainProbeDisabledStart','status':'PASS',
                 'handoffApproved':False,'sourceCommit':'a'*40,'buildId':'disabled',
                 'aeVersion':'25.6.0.101','AEGP_load':'OBSERVED','SYNC-001':'NOT RUN'}
            path.write_text(json.dumps(row),encoding='utf-8')
            original_root=gate.ROOT
            try:
                gate.ROOT=root
                summary=gate.read_child_evidence(
                    path,'FSTRChainProbeDisabledStart','PASS',evidence_root=root)
            finally:
                gate.ROOT=original_root
            self.assertEqual(summary['sourceCommit'],'a'*40)
            self.assertEqual(summary['buildId'],'disabled')

    def test_result_envelope_uses_last_valid_json_line(self):
        row=gate._result_envelope('noise\n{"evidence":"/tmp/a","status":"PASS"}\n')
        self.assertEqual(row,{'evidence':'/tmp/a','status':'PASS'})

if __name__=='__main__':
    unittest.main()
