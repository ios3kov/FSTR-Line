"""Symbol collisions in owned fixtures only; never a private AE invocation."""
import hashlib
import importlib.util
import json
import plistlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "queue_collision_control", ROOT / "research/ae-notifications/queue_static.py")
q = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(q)


def output(text):
    data = text.encode()
    return {"text": text, "exitCode": 0, "complete": True, "reason": None,
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


class Fixture:
    def __init__(self, root):
        self.app = (root / "Owned collision fixture.app").resolve()
        (self.app / "Contents").mkdir(parents=True)
        meta = {"CFBundleIdentifier": "org.fstr.collision-fixture",
                "CFBundleShortVersionString": "owned", "CFBundleVersion": "owned.1"}
        (self.app / "Contents/Info.plist").write_bytes(plistlib.dumps(meta))
        self.policy = {"aeBundleId": meta["CFBundleIdentifier"],
                       "aeShortVersion": "owned", "aeBundleVersion": "owned.1", "modules": {}}
        self.paths, self.symbols, self.full, self.external = {}, {}, {}, {}
        self.calls = []
        for index, (key, names) in enumerate(q.REQUIRED.items()):
            path = self.app / f"Contents/{key}.dylib"
            path.write_bytes(f"owned-not-mach-o-{key}".encode())
            self.paths[key] = path
            self.policy["modules"][key] = {
                "relativePath": f"Contents/{key}.dylib", "sha256": q.fingerprint(path),
                "uuid": f"00000000-0000-4000-8000-{index + 1:012d}"}
            self.symbols[key] = {name: 4096 + n * 16 for n, name in enumerate(names)}
            self.full[key] = "".join(f"{a:016x} T {n}\n" for n, a in self.symbols[key].items())
            self.external[key] = self.full[key]

    def run(self, args, **_limits):
        self.calls.append(args)
        if args[-1] == "--version":
            return output("Owned synthetic tool\n")
        key = next(k for k, path in self.paths.items() if str(path) == args[-1])
        if args[1] == "dwarfdump":
            return output(f"UUID: {self.policy['modules'][key]['uuid']} (arm64) fixture\n")
        if args[1] == "nm":
            return output(self.external[key] if "-gU" in args else self.full[key])
        name = args[args.index("--dis-symname") + 1]
        address = self.symbols[key][name]
        return output(f"fixture:\n{name}:\n{address:016x}\tadd x0, x0, #1\n{address+4:016x}\tret\n")


class CollisionTests(unittest.TestCase):
    def test_uploaded_blocked_evidence_is_preserved_not_promoted(self):
        path = ROOT / "docs/TEST_RECORDS/evidence/queue-6c22da4-blocked.json"
        raw = path.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         "d4b1fcdc16bf18439cc277fb573a3e51e748e5351e910a7e4bd06d837e98619a")
        report = json.loads(raw)
        self.assertEqual(report["collectionStatus"], "BLOCKED")
        self.assertEqual(report["reason"], "DUPLICATE_TEXT_SYMBOL")
        self.assertEqual(report["SYNC-001"], "NOT RUN")
        self.assertTrue(all(not row["bodies"] for row in report["modules"].values()))

    def test_unrelated_duplicates_do_not_prevent_requested_collection(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td))
            f.full["BEE"] += "00003000 t __ZL5ownedi\n00004000 t __ZL5ownedi\n"
            report = q.collect(f.app, f.policy, f.run)
        self.assertEqual(report["collectionStatus"], "PASS", report)
        self.assertEqual(sum(len(v["bodies"]) for v in report["modules"].values()), 7)
        self.assertEqual(report["SYNC-001"], "NOT RUN")
        self.assertFalse(report["privateInvocationAllowed"])
        self.assertEqual(set(report["claims"].values()), {"UNPROVEN"})

    def test_same_address_repetition_is_not_a_different_target(self):
        self.assertEqual(q.text_symbols("1000 t _same\n1000 t _same\n"), {"_same": 4096})
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td))
            f.full["BEE"] += f.full["BEE"].splitlines()[0] + "\n"
            self.assertEqual(q.collect(f.app, f.policy, f.run)["collectionStatus"], "PASS")

    def test_index_retains_all_distinct_addresses_and_strict_view_refuses(self):
        text = "1000 t _same\n2000 t _same\n2000 t _same\n3000 T _other\n4000 S _data\n"
        self.assertEqual(q.text_symbol_table(text), {"_same": {4096, 8192}, "_other": {12288}})
        with self.assertRaisesRegex(q.Blocked, "DUPLICATE_TEXT_SYMBOL"):
            q.text_symbols(text)

    def test_requested_collisions_in_either_module_block_before_disassembly(self):
        for key in q.REQUIRED:
            with self.subTest(module=key), tempfile.TemporaryDirectory() as td:
                f = Fixture(Path(td))
                symbol = q.REQUIRED[key][0]
                f.full[key] += f"00008000 t {symbol}\n"
                report = q.collect(f.app, f.policy, f.run)
                self.assertEqual(report["collectionStatus"], "BLOCKED", report)
                self.assertEqual(report["reason"], f"AMBIGUOUS_REQUESTED_TEXT_SYMBOL:{key}:{symbol}")
                self.assertEqual(report["ambiguousTarget"]["addresses"], ["0x1000", "0x8000"])
                self.assertFalse(any("--disassemble" in args for args in f.calls))

    def test_ambiguous_inventory_lead_is_not_silently_selectable(self):
        lead = "_BEE_Globals_ownedProjectLead"  # synthetic, not an Adobe name
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td))
            f.full["BEE"] += f"00003000 t {lead}\n00004000 t {lead}\n"
            report = q.collect(f.app, f.policy, f.run)
            self.assertEqual(report["collectionStatus"], "PASS", report)
            item = next(x for x in report["modules"]["BEE"]["inventory"] if x["symbol"] == lead)
            self.assertIsNone(item["address"])
            self.assertEqual(item["distinctAddressCount"], 2)
            f.calls.clear()
            report = q.collect(f.app, f.policy, f.run, inspect_symbols=["BEE:" + lead])
            self.assertEqual(report["collectionStatus"], "BLOCKED", report)
            self.assertFalse(any("--disassemble" in args for args in f.calls))

    def test_external_view_must_remain_subset_of_full_table(self):
        for missing in (False, True):
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as td:
                f = Fixture(Path(td))
                f.full["BEE"] += "00003000 t _dup\n00004000 T _dup\n"
                f.external["BEE"] += f"{'00005000' if missing else '00004000'} T _dup\n"
                report = q.collect(f.app, f.policy, f.run)
                self.assertEqual(report["collectionStatus"], "BLOCKED" if missing else "PASS", report)
                if missing:
                    self.assertFalse(any("--disassemble" in args for args in f.calls))

    def test_diagnostics_are_bounded_and_retain_counts(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td))
            for n in range(20):
                for address in range(30):
                    f.full["BEE"] += f"{0x3000 + address * 4:08x} t _owned{n:02d}\n"
            report = q.collect(f.app, f.policy, f.run)
        self.assertEqual(report["collectionStatus"], "PASS", report)
        diagnostics = report["modules"]["BEE"]["nmAmbiguities"]
        self.assertEqual(diagnostics["definedNameCount"], 20)
        self.assertEqual(len(diagnostics["samples"]), 12)
        self.assertTrue(diagnostics["samplesTruncated"])
        for sample in diagnostics["samples"]:
            self.assertEqual(len(sample["addresses"]), 4)
            self.assertEqual(sample["distinctAddressCount"], 30)
            self.assertTrue(sample["addressesTruncated"])

    def test_duplicate_handling_does_not_relax_malformed_output(self):
        for text in ("warning: incomplete", " U _undefined", "1000 T _x\nnot nm output"):
            with self.subTest(text=text), self.assertRaises(q.Blocked):
                q.text_symbol_table(text)

    @unittest.skipUnless(sys.platform == "darwin", "requires actual Apple nm/linker; not AE")
    def test_real_two_translation_unit_macho_collisions(self):
        # Two independently compiled translation units keep same-named local
        # functions at different addresses in one dylib. No Adobe code or SDK.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            sources = []
            for n in (1, 2):
                source = root / f"unit{n}.cpp"
                source.write_text(
                    'static __attribute__((noinline)) int duplicate_local(int x) '
                    f'{{return x+{n};}}\n'
                    f'extern "C" int fstr_owned_entry{n}(int x) {{return duplicate_local(x);}}\n')
                sources.append(str(source))
            binary = root / "owned.dylib"
            build = q.run_tool(["xcrun", "clang++", "-arch", "arm64", "-dynamiclib", "-O0",
                                *sources, "-o", str(binary)])
            self.assertTrue(build["complete"], build)
            nm = q.run_tool(["xcrun", "nm", "-arch", "arm64", "-U", str(binary)], max_bytes=q.MAX_NM)
            self.assertTrue(nm["complete"], nm)
            table = q.text_symbol_table(nm["text"])
            collisions = {n: a for n, a in table.items() if len(a) > 1}
            self.assertTrue(any("duplicate_local" in n for n in collisions), nm["text"])
            # The old strict view reproduces the uploaded report's guard. This
            # does not identify which symbol collided in the user's Adobe file.
            with self.assertRaisesRegex(q.Blocked, "DUPLICATE_TEXT_SYMBOL"):
                q.text_symbols(nm["text"])
            roots = {"BEE": ("_fstr_owned_entry1",), "AfterFXLib": ("_fstr_owned_entry2",)}
            with mock.patch.object(q, "REQUIRED", roots):
                f = Fixture(root)
                for key, path in f.paths.items():
                    path.write_bytes(binary.read_bytes())
                    uid = q.run_tool(["xcrun", "dwarfdump", "--uuid", str(path)])
                    self.assertTrue(uid["complete"], uid)
                    f.policy["modules"][key].update(sha256=q.fingerprint(path), uuid=q.arm64_uuid(uid["text"]))
                report = q.collect(f.app, f.policy)
            self.assertEqual(report["collectionStatus"], "PASS", report)
            self.assertEqual(report["expectedBodyCount"], 2)
            self.assertEqual(report["SYNC-001"], "NOT RUN")
            self.assertFalse(report["privateInvocationAllowed"])
            self.assertTrue(all(v["nmAmbiguities"]["definedNameCount"] > 0
                                for v in report["modules"].values()))


if __name__ == "__main__":
    unittest.main()
