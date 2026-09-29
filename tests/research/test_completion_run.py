import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('completion_run',ROOT/'research/ae-notifications/completion_run.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)


class CompletionRunTests(unittest.TestCase):
    def test_owned_fixture_guard_and_separate_read(self):
        fixture={'compId':16,'layerId':29,'name':'FSTR completion test cf59d1b55ebb'}
        with mock.patch.object(r,'execute',return_value={**fixture,'enabled':True}) as execute:
            self.assertEqual(r.read_fixture(Path('/unused'),'oracle',fixture),{**fixture,'enabled':True})
            body=execute.call_args.args[2]
            self.assertIn('x.id===16',body)
            self.assertIn('l.id!==29',body)
            self.assertIn('l.name!=="FSTR owned test layer"',body)
            self.assertNotIn('addComp',body)
            self.assertNotIn('l.enabled=',body)

    def test_oracle_rejects_identity_and_state_mismatch(self):
        fixture={'compId':16,'layerId':29,'name':'FSTR completion test cf59d1b55ebb'}
        for changed in ({**fixture,'enabled':False},
                        {**fixture,'layerId':30,'enabled':True},
                        {**fixture,'enabled':1},
                        {'enabled':True}):
            with self.subTest(changed=changed),self.assertRaises(RuntimeError):
                r.verify_read(changed,fixture,True)

    def test_reuse_identity_rejects_unowned_name(self):
        with self.assertRaises(ValueError):
            r.fixture_guard({'compId':16,'layerId':29,'name':'User comp'})

    def test_preflight_refusal_precedes_script_and_process(self):
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(r.completion_preflight,'preflight',side_effect=ValueError('mismatch')), \
             mock.patch.object(r,'execute') as execute, \
             mock.patch.object(r.subprocess,'Popen') as spawn:
            output=Path(td)/'not-created'
            with self.assertRaises(ValueError):r.run(Path('/fixture'),42,output)
            self.assertFalse(output.exists());execute.assert_not_called();spawn.assert_not_called()

    def test_script_timeout_has_no_retry(self):
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(r.context,'run_jsx',return_value={'ok':False,'timedOut':True}) as bridge:
            with self.assertRaises(RuntimeError):r.execute(Path(td),'fixture','var result={};')
            self.assertEqual(bridge.call_count,1)

    def test_existing_script_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as td, mock.patch.object(r.context,'run_jsx') as bridge:
            path=Path(td)/'fixture.jsx';path.write_text('original')
            with self.assertRaises(FileExistsError):r.execute(Path(td),'fixture','var result={};')
            self.assertEqual(path.read_text(),'original');bridge.assert_not_called()


if __name__=='__main__':unittest.main()
