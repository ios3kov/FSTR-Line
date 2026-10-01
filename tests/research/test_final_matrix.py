import importlib.util,json,subprocess,tempfile,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[2]
SPEC=importlib.util.spec_from_file_location('runtime_probe',ROOT/'research/ae-notifications/runtime_probe.py')
probe=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(probe)

class FinalMatrixTests(unittest.TestCase):
    def test_find_pids_matches_main_binary_only(self):
        done=mock.Mock(returncode=0,stdout=' 12 /A/After Effects\n 13 /A/After Effects Helper\n',stderr='')
        runner=mock.Mock(return_value=done)
        self.assertEqual(probe.find_pids(Path('/A/After Effects'),runner=runner),[12])
        self.assertEqual(runner.call_args.args[0],['/bin/ps','-axo','pid=,comm='])

    def test_jsx_command_uses_application_id_and_file(self):
        fake=mock.Mock(return_value=mock.Mock(returncode=0,stdout='OK\n',stderr=''))
        with mock.patch.object(probe.subprocess,'run',fake):
            row=probe.run_jsx('com.adobe.AfterEffects.application',Path('/tmp/FSTR Test.jsx'))
        args=fake.call_args.args[0]
        self.assertEqual(args[:2],['/usr/bin/osascript','-e'])
        self.assertIn('DoScriptFile POSIX file',args[2])
        self.assertIn('com.adobe.AfterEffects.application',args[2])
        self.assertTrue(row['ok'])

    def test_run_jsx_timeout_is_nonfatal_result(self):
        timeout=subprocess.TimeoutExpired(cmd=['/usr/bin/osascript'],timeout=1,output='partial',stderr='slow')
        with mock.patch.object(probe.subprocess,'run',side_effect=timeout):
            row=probe.run_jsx('com.adobe.AfterEffects.application',Path('/tmp/FSTR-Burst.jsx'),timeout=1)
        self.assertFalse(row['ok'])
        self.assertTrue(row['timedOut'])
        self.assertEqual(row['returnCode'],None)
        self.assertIn('continues',row['error'])

    def test_completed_prefix_stops_at_first_incomplete_phase(self):
        phases=[{'label':'a'},{'label':'b'},{'label':'c'}]
        rows=[{'kind':'snapshot-after','session':'pre-restart','phase':'a'},
              {'kind':'snapshot-before','session':'pre-restart','phase':'b'},
              {'kind':'snapshot-after','session':'pre-restart','phase':'c'}]
        self.assertEqual(probe.completed_phase_prefix(phases,rows),1)

    def test_resume_requires_same_pid_breakpoints_and_clean_abort_detach(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); old=root/'fstr-final-old'; session=old/'pre-restart'
            session.mkdir(parents=True)
            evidence=old/'evidence.jsonl'
            evidence.write_text('{"kind":"snapshot-after","session":"pre-restart","phase":"a"}\n')
            binary=Path(td)/'After Effects'; binary.write_text('')
            candidates={'breakpoints':[{'label':'x'}],
                        'preRestart':[{'label':'a'},{'label':'b'}]}
            (session/'plan.json').write_text(json.dumps({
                'runId':'owned-resume','pid':42,'executable':str(binary),'breakpoints':candidates['breakpoints']}))
            (session/'result.json').write_text(json.dumps({
                'pid':42,'status':'BLOCKED','stage':'aborted','detached':True}))
            # Legacy result-only evidence cannot certify debugger shutdown.
            self.assertIsNone(probe.find_resume_candidate(root,binary,42,candidates))
            (session/'observer-parent.json').write_text(json.dumps({
                'runId':'owned-resume','resumeEligible':True,
                'planSha256':probe.sha256(session/'plan.json'),
                'controllerResultSha256':probe.sha256(session/'result.json'),
                'debuggerExitCode':0,'debuggerReaped':True,'shutdownTimedOut':False,
                'forcedTermination':False,'cleanupErrors':[]}))
            found=probe.find_resume_candidate(root,binary,42,candidates)
            self.assertIsNotNone(found)
            self.assertEqual(found['completed'],1)
            self.assertIsNone(probe.find_resume_candidate(root,binary,43,candidates))

    def test_snapshot_reads_owned_file_not_applescript_return_value(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            def fake_run(bundle_id,script_path,timeout=15):
                target=script_path.parent/'snapshot-target.txt'
                output=Path(target.read_text(encoding='utf-8').strip())
                output.write_text('comp=Comp_A|layers=2|time=1.000000',encoding='utf-8')
                return {'ok':True,'timedOut':False,'elapsedMs':12.5,'stdout':'0','stderr':'','returnCode':0}
            with mock.patch.object(probe,'run_jsx',side_effect=fake_run):
                row=probe.snapshot('com.adobe.AfterEffects.application',root)
        self.assertTrue(row['ok'])
        self.assertEqual(row['value'],'comp=Comp_A|layers=2|time=1.000000')
        self.assertTrue(row['bridgeOk'])

    def test_snapshot_bridge_success_without_output_is_not_valid_oracle(self):
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(probe,'run_jsx',return_value={
                'ok':True,'timedOut':False,'elapsedMs':1.0,'stdout':'0','stderr':'','returnCode':0
            }):
                row=probe.snapshot('com.adobe.AfterEffects.application',Path(td))
        self.assertFalse(row['ok'])
        self.assertIn('not created',row['error'])

    def test_snapshot_changed_logic_is_raw_state_evidence_only(self):
        self.assertNotEqual('layers=2','layers=3')

if __name__=='__main__': unittest.main()
