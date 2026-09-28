import hashlib, importlib.util, os, re, sys, tempfile, unittest
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
                   "sha256":hashlib.sha256(b"fixture").hexdigest(),"uuid":"fixture","symbols":["candidate"]}
    def tearDown(self): self.tmp.cleanup()

    def test_exact_hash_runs_streamed_nm_and_lldb_lookup(self):
        with mock.patch.object(focused,"stream_filtered",
              return_value=(0,["0000 BEE_Layer"],False,9,"")), \
             mock.patch.object(focused,"run_text",
              return_value=(0,"image lookup BEE_Layer candidate")):
            row=focused.focused_module(self.app.resolve(),self.spec,["BEE_Layer"],["BEE_Layer"])
        self.assertEqual(row["status"],"PASS")
        self.assertEqual(row["nmHits"],["0000 BEE_Layer"])
        self.assertEqual(row["nmInputBytes"],9)
        self.assertIn("candidate",row["lldbOutput"])

    def test_hash_mismatch_blocks_before_tools(self):
        bad=dict(self.spec,sha256="0"*64)
        with mock.patch.object(focused,"stream_filtered") as stream, mock.patch.object(focused,"run_text") as run:
            row=focused.focused_module(self.app.resolve(),bad,["BEE_Layer"],["BEE_Layer"])
        self.assertEqual(row["status"],"BLOCKED"); stream.assert_not_called(); run.assert_not_called()

    def test_escape_path_rejected(self):
        outside=self.root/"outside"; outside.write_bytes(b"fixture")
        bad=dict(self.spec,relativePath="../outside",sha256=hashlib.sha256(b"fixture").hexdigest())
        with self.assertRaises((ValueError,FileNotFoundError)):
            focused.focused_module(self.app.resolve(),bad,["x"],["x"])

    def test_lldb_output_bound(self):
        fake=mock.Mock(return_value=mock.Mock(returncode=0,stdout="x"*(focused.MAX_TEXT+1),stderr=""))
        with mock.patch.object(focused.subprocess,"run",fake), self.assertRaises(ValueError):
            focused.run_text(["fixture"])

    def test_stream_filter_handles_more_than_old_four_megabyte_limit(self):
        payload="x"*1024+"\n"
        script=("import sys\n"
                "line="+repr(payload)+"\n"
                "for _ in range(5000): sys.stdout.write(line)\n"
                "sys.stdout.write('TARGET BEE_Layer CmdParamChanged\\n')\n")
        code,hits,limited,total,_=focused.stream_filtered(
            [sys.executable,"-c",script],re.compile("BEE_Layer"),timeout=20,max_input=16*1024*1024)
        self.assertEqual(code,0)
        self.assertEqual(hits,["TARGET BEE_Layer CmdParamChanged"])
        self.assertFalse(limited)
        self.assertGreater(total,4*1024*1024)

    def test_stream_filter_caps_retained_hits_not_input(self):
        script="import sys\nfor i in range(20): print('BEE_Layer '+str(i))\n"
        code,hits,limited,total,_=focused.stream_filtered(
            [sys.executable,"-c",script],re.compile("BEE_Layer"),timeout=10,max_input=1024*1024,max_hits=3)
        self.assertEqual(code,0); self.assertEqual(len(hits),3); self.assertTrue(limited); self.assertGreater(total,0)

    def test_stream_filter_hard_input_cap_stops_owned_child(self):
        script="import sys\nwhile True: sys.stdout.write('x'*65536); sys.stdout.flush()\n"
        with self.assertRaises(ValueError):
            focused.stream_filtered([sys.executable,"-c",script],re.compile("never"),timeout=10,max_input=128*1024)

if __name__=="__main__": unittest.main()
