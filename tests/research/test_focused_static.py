import hashlib, importlib.util, json, tempfile, unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location("focused",ROOT/"research/ae-notifications/focused_static.py")
focused=importlib.util.module_from_spec(spec); spec.loader.exec_module(focused)

class FocusedTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.app=self.root/"AE.app"; (self.app/"Contents/Frameworks").mkdir(parents=True)
        self.mod=self.app/"Contents/Frameworks/BEE.dylib"; self.mod.write_bytes(b"fixture")
        self.spec={"relativePath":"Contents/Frameworks/BEE.dylib",
                   "sha256":hashlib.sha256(b"fixture").hexdigest(),"uuid":"fixture","symbols":["_candidate"]}
    def tearDown(self): self.tmp.cleanup()
    def test_exact_hash_runs_nm_and_lldb_and_filters(self):
        with mock.patch.object(focused,"run_text",side_effect=[
            (0,"0000 candidate BEE_Layer\n0001 irrelevant\n"),
            (0,"image uuid fixture\ndisassembly candidate\n")]):
            row=focused.focused_module(self.app.resolve(),self.spec,["BEE_Layer"])
        self.assertEqual(row["status"],"PASS")
        self.assertEqual(row["nmHits"],["0000 candidate BEE_Layer"])
        self.assertIn("disassembly",row["lldbOutput"])
    def test_hash_mismatch_blocks_before_tools(self):
        bad=dict(self.spec,sha256="0"*64)
        with mock.patch.object(focused,"run_text") as run:
            row=focused.focused_module(self.app.resolve(),bad,["BEE_Layer"])
        self.assertEqual(row["status"],"BLOCKED"); run.assert_not_called()
    def test_escape_path_rejected(self):
        outside=self.root/"outside"; outside.write_bytes(b"fixture")
        bad=dict(self.spec,relativePath="../outside",sha256=hashlib.sha256(b"fixture").hexdigest())
        with self.assertRaises((ValueError,FileNotFoundError)): focused.focused_module(self.app.resolve(),bad,["x"])
    def test_tool_output_bound(self):
        fake=mock.Mock(return_value=mock.Mock(returncode=0,stdout="x"*(focused.MAX_TEXT+1),stderr=""))
        with mock.patch.object(focused.subprocess,"run",fake), self.assertRaises(ValueError):
            focused.run_text(["fixture"])

if __name__=="__main__": unittest.main()
