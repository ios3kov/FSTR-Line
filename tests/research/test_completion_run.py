import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('completion_run',ROOT/'research/ae-notifications/completion_run.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)


class CompletionRunTests(unittest.TestCase):
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
