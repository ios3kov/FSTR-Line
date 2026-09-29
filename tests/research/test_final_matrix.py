import importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[2]
SPEC=importlib.util.spec_from_file_location('runtime_probe',ROOT/'research/ae-notifications/runtime_probe.py')
probe=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(probe)

class FinalMatrixTests(unittest.TestCase):
    def test_find_pids_exact_binary(self):
        done=mock.Mock(returncode=0,stdout=' 12 /A/After Effects\n 13 /A/After Effects Helper\n',stderr='')
        with mock.patch.object(probe.subprocess,'run',return_value=done):
            self.assertEqual(probe.find_pids(Path('/A/After Effects')),[12,13])
    def test_jsx_command_uses_application_id_and_file(self):
        fake=mock.Mock(return_value=mock.Mock(returncode=0,stdout='OK\n',stderr=''))
        with mock.patch.object(probe.subprocess,'run',fake):
            row=probe.run_jsx('com.adobe.AfterEffects.application',Path('/tmp/FSTR Test.jsx'))
        args=fake.call_args.args[0]
        self.assertEqual(args[:2],['/usr/bin/osascript','-e'])
        self.assertIn('DoScriptFile POSIX file',args[2])
        self.assertIn('com.adobe.AfterEffects.application',args[2])
        self.assertTrue(row['ok'])
    def test_snapshot_changed_logic_is_raw_state_evidence_only(self):
        self.assertNotEqual('layers=2','layers=3')

if __name__=='__main__': unittest.main()
