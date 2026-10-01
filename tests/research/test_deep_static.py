import hashlib,importlib.util,json,re,tempfile,unittest,zipfile
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[2]
SPEC=importlib.util.spec_from_file_location("deep_static",ROOT/"research/ae-notifications/deep_static.py")
d=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(d)

class DeepStaticTests(unittest.TestCase):
    def test_main_archives_blocked_when_disassembly_fails(self):
        targets=json.loads((ROOT/"research/ae-notifications/deep_targets.json").read_text())
        meta={"bundleId":targets["aeBundleId"],"shortVersion":targets["aeShortVersion"],
              "bundleVersion":targets["aeBundleVersion"]}
        with tempfile.TemporaryDirectory() as td:
            app=Path(td)/"AE.app"
            with mock.patch.object(d.collect_app,"identity",return_value=(app,app,meta)), \
                 mock.patch.object(d,"verify_module",return_value=(app,{"status":"PASS"})), \
                 mock.patch.object(d,"active_candidates",return_value={"exitCode":0,"limited":False}), \
                 mock.patch.object(d,"lldb_known",return_value={"exitCode":1,"output":"fixture error"}):
                self.assertEqual(d.main(["--app",str(app),"--output",td]),2)
            archives=list(Path(td).glob("*.zip"))
            self.assertEqual(len(archives),1)
            with zipfile.ZipFile(archives[0]) as z:
                report=json.loads(z.read("report.json"))
            self.assertEqual(report["status"],"BLOCKED")
            self.assertEqual(report["SYNC-001"],"NOT RUN")

    def test_tool_failures_and_truncation_block_report(self):
        good={"activeCompCandidates":{"BEE":{"exitCode":0,"limited":False}},
              "knownFunctionStatic":{"BEE":{"exitCode":0}}}
        self.assertTrue(d.analysis_complete(good))
        for code,limited in ((1,False),(0,True),(None,False)):
            report={**good,"activeCompCandidates":{"BEE":{"exitCode":code,"limited":limited}}}
            self.assertFalse(d.analysis_complete(report))
        self.assertFalse(d.analysis_complete({**good,"knownFunctionStatic":{"BEE":{"exitCode":1}}}))
        self.assertFalse(d.analysis_complete({"activeCompCandidates":{},"knownFunctionStatic":{}}))

    def test_active_regex_matches_both_word_orders(self):
        rx=re.compile(r"(?i)((active|activate|current|front).*(comp|composition|item|viewer|pano))|((comp|composition|item|viewer|pano).*(active|activate|current|front))")
        self.assertRegex("SetActiveComposition",rx)
        self.assertRegex("CCompPano::Activate",rx)
        self.assertNotRegex("BEE_Layer::SetEnabled",rx)

    def test_hash_or_uuid_mismatch_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            app=Path(td)/"AE.app"; path=app/"Contents/Frameworks/BEE.dylib"
            path.parent.mkdir(parents=True); path.write_bytes(b"fixture")
            spec={"relativePath":"Contents/Frameworks/BEE.dylib","sha256":"0"*64,
                  "uuid":"01234567-89ab-cdef-0123-456789abcdef"}
            with mock.patch.object(d,"module_uuid",return_value=spec["uuid"]):
                resolved,row=d.verify_module(app.resolve(), "BEE", spec)
            self.assertIsNone(resolved); self.assertEqual(row["status"],"BLOCKED")

if __name__=="__main__": unittest.main()
