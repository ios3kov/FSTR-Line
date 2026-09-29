import hashlib,importlib.util,re,tempfile,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[2]
SPEC=importlib.util.spec_from_file_location("deep_static",ROOT/"research/ae-notifications/deep_static.py")
d=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(d)

class DeepStaticTests(unittest.TestCase):
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
