"""Owned/synthetic controls. None of these tests runs or subscribes to AE."""
import hashlib
import importlib.util
import json
import os
import plistlib
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("queue_static", ROOT / "research/ae-notifications/queue_static.py")
q = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(q)


def output(text, code=0, complete=True):
    raw = text.encode()
    return {"text": text, "exitCode": code, "complete": complete,
            "reason": None, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def body(symbol, address):
    return f"fixture:\n{symbol}:\n{address:016x}\tadd x0, x0, #1\n{address + 4:016x}\tret\n"


class Fixture:
    """Fabricated binaries/UUIDs identify only this fixture, never an Adobe build."""
    def __init__(self, root):
        self.app = root / "Owned AE Fixture.app"
        (self.app / "Contents").mkdir(parents=True)
        self.policy = {"aeBundleId": "org.fstr.fixture", "aeShortVersion": "fixture",
                       "aeBundleVersion": "fixture.1", "modules": {}}
        metadata = {"CFBundleIdentifier": "org.fstr.fixture",
                    "CFBundleShortVersionString": "fixture", "CFBundleVersion": "fixture.1"}
        (self.app / "Contents/Info.plist").write_bytes(plistlib.dumps(metadata))
        self.symbols = {}
        self.paths = {}
        self.calls = []
        for index, (key, names) in enumerate(q.REQUIRED.items()):
            path = self.app / f"Contents/{key}.dylib"
            path.write_bytes((key + "-synthetic-not-mach-o").encode())
            self.paths[key] = path
            self.policy["modules"][key] = {"relativePath": f"Contents/{key}.dylib",
                "sha256": q.fingerprint(path), "uuid": f"00000000-0000-4000-8000-{index + 1:012d}"}
            self.symbols[key] = {name: 4096 + i * 16 for i, name in enumerate(names)}

    def run(self, args, **_limits):
        self.calls.append(args)
        if args[-1] == "--version":
            return output("Synthetic fixture tool, not Apple LLVM\n")
        key = next(k for k, path in self.paths.items() if str(path) == args[-1])
        if args[1] == "dwarfdump":
            uid = self.policy["modules"][key]["uuid"]
            return output(f"UUID: {uid} (arm64) fixture\n")
        if args[1] == "nm":
            # The completion registrar exists only in the full table.
            names = list(self.symbols[key])
            if "-gU" in args:
                names = names[:1]
            return output("".join(f"{self.symbols[key][n]:016x} T {n}\n" for n in names))
        symbol = args[args.index("--dis-symname") + 1]
        return output(body(symbol, self.symbols[key][symbol]))


class QueueStaticTests(unittest.TestCase):
    def test_uuid_selects_arm64_not_first_slice(self):
        text = ("UUID: 00000000-0000-4000-8000-000000000001 (x86_64) fixture\n"
                "UUID: 00000000-0000-4000-8000-000000000002 (arm64) fixture\n")
        self.assertTrue(q.arm64_uuid(text).endswith("2"))
        for wrong in ("", text.replace("(arm64)", "(arm64e)"), text + text):
            with self.subTest(text=wrong), self.assertRaises(q.Blocked):
                q.arm64_uuid(wrong)

    def test_nm_definitions_and_diagnostics(self):
        self.assertEqual(q.text_symbols("fixture:\n00001000 T _public\n00001004 t _local\n00002000 S _data\n"),
                         {"_public": 4096, "_local": 4100})
        for text in ("warning: incomplete", "00001000 T _x\n00001004 T _x", " U _undefined"):
            with self.subTest(text=text), self.assertRaises(q.Blocked):
                q.text_symbols(text)

    def test_body_requires_exact_positive_evidence(self):
        cases = ("", "_wanted:\n", body("_other", 4096), body("_wanted", 4100),
                 body("_wanted", 4096) + "_other:\n", body("_wanted", 4096) * 2,
                 body("_wanted", 4096).replace("1004", "1008"),
                 body("_wanted", 4096).replace("ret", "<unknown>"),
                 body("_wanted", 4096) + "warning: incomplete\n")
        for text in cases:
            with self.subTest(text=text), self.assertRaises(q.Blocked):
                q.inspect_body(text, "_wanted", 4096)
        self.assertEqual(q.inspect_body(body("_wanted", 4096), "_wanted", 4096)["instructionCount"], 2)

    def test_compact_llvm_addresses_from_real_owned_object(self):
        text = "fixture.o:\n(__TEXT,__text) section\n_owned:\n       0:\tadd w0, w0, #0x1\n       4:\tret\n"
        self.assertEqual(q.inspect_body(text, "_owned", 0)["instructionCount"], 2)

    @unittest.skipUnless(sys.platform == "linux" and shutil.which("clang++") and shutil.which("llvm-objdump"),
                         "requires Linux cross-LLVM tools; not an AE test")
    def test_real_llvm_on_owned_arm64_object(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "owned.cpp"
            binary = Path(td) / "owned.o"
            source.write_text('extern "C" int fstr_queue_static_control(int x) { return x + 1; }\n')
            built = q.run_tool(["clang++", "-target", "arm64-apple-macos11", "-O1", "-c", str(source), "-o", str(binary)])
            self.assertTrue(built["complete"], built)
            result = q.run_tool(["llvm-objdump", "--macho", "--arch=arm64", "--disassemble",
                                 "--no-show-raw-insn", "--dis-symname", "_fstr_queue_static_control", str(binary)])
            self.assertTrue(result["complete"], result)
            self.assertGreater(q.inspect_body(result["text"], "_fstr_queue_static_control", 0)["instructionCount"], 0)

    def test_branch_site_is_not_a_runtime_thread_claim(self):
        text = body("_owned", 4096).replace("add x0, x0, #1", "blr x8")
        self.assertEqual(q.inspect_body(text, "_owned", 4096)["branchSites"],
                         [{"address": "0x1000", "instruction": "blr x8"}])

    def test_collects_all_roots_without_approving_private_calls(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td))
            report = q.collect(f.app, f.policy, f.run)
        self.assertEqual(report["collectionStatus"], "PASS", report)
        self.assertEqual(report["SYNC-001"], "NOT RUN")
        self.assertIs(report["privateInvocationAllowed"], False)
        self.assertEqual(set(report["claims"].values()), {"UNPROVEN"})
        self.assertEqual(sum(len(m["bodies"]) for m in report["modules"].values()), 7)
        registrar = next(x for x in report["modules"]["AfterFXLib"]["inventory"]
                         if "SignalIFvP15BEE_UndoContext" in x["symbol"])
        self.assertEqual(registrar["visibility"], "defined-only-in-full-nm")
        self.assertNotIn(str(f.app), json.dumps(report))
        self.assertFalse(any("lldb" in a or "--attach" in a for a in f.calls))

    def test_paths_are_redacted_before_json_escapes_unicode_and_quotes(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td) / 'Кириллица "quoted"')
            report = q.collect(f.app, f.policy, f.run)
            self.assertEqual(report["collectionStatus"], "PASS", report)
            encoded = json.dumps(report, ensure_ascii=False)
            self.assertNotIn("Кириллица", encoded)
            self.assertNotIn("quoted", encoded)
            self.assertIn("<AE_APP>", encoded)

    def test_zero_exit_with_missing_body_is_not_pass(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td))
            def runner(args, **kw):
                if "--disassemble" in args:
                    return output("fixture:\n")
                return f.run(args, **kw)
            report = q.collect(f.app, f.policy, runner)
        self.assertEqual(report["collectionStatus"], "BLOCKED")
        self.assertEqual(report["reason"], "REQUESTED_BODY_MISSING_OR_AMBIGUOUS")

    def test_build_and_hash_refuse_before_disassembly(self):
        for mismatch in ("build", "first-hash", "second-hash"):
            with self.subTest(mismatch=mismatch), tempfile.TemporaryDirectory() as td:
                f = Fixture(Path(td))
                if mismatch == "build":
                    f.policy["aeBundleVersion"] = "wrong"
                else:
                    key = "BEE" if mismatch == "first-hash" else "AfterFXLib"
                    f.policy["modules"][key]["sha256"] = "0" * 64
                report = q.collect(f.app, f.policy, f.run)
                self.assertEqual(report["collectionStatus"], "BLOCKED")
                self.assertFalse(any("nm" in a or "--disassemble" in a for a in f.calls))

    def test_wrong_architecture_and_uuid_refuse(self):
        for kind in ("arch", "uuid"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as td:
                f = Fixture(Path(td))
                def runner(args, **kw):
                    row = f.run(args, **kw)
                    if args[1] == "dwarfdump":
                        row["text"] = row["text"].replace("arm64", "x86_64") if kind == "arch" else \
                            "UUID: ffffffff-ffff-4fff-8fff-ffffffffffff (arm64) fixture\n"
                    return row
                self.assertEqual(q.collect(f.app, f.policy, runner)["collectionStatus"], "BLOCKED")
                self.assertFalse(any("nm" in a for a in f.calls))

    def test_escaping_symlink_and_parent_path_are_refused(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td))
            outside = Path(td) / "outside"
            outside.write_bytes(b"untouched")
            link = f.app / "Contents/link"
            link.symlink_to(outside)
            for relative in ("Contents/link", "../outside", str(outside)):
                with self.subTest(relative=relative), self.assertRaises(q.Blocked):
                    q.module_path(f.app, relative)
            self.assertEqual(outside.read_bytes(), b"untouched")

    def test_missing_required_symbol_and_export_inconsistency_block(self):
        for kind in ("missing", "inconsistent", "empty"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as td:
                f = Fixture(Path(td))
                def runner(args, **kw):
                    row = f.run(args, **kw)
                    if args[1] == "nm":
                        if kind == "empty":
                            return output("")
                        if kind == "missing":
                            return output("00002000 T _unrelated\n")
                        if "-gU" in args:
                            return output(row["text"].replace("0000000000001000", "0000000000002000"))
                    return row
                self.assertEqual(q.collect(f.app, f.policy, runner)["collectionStatus"], "BLOCKED")

    def test_persistent_mid_collection_replacement_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td))
            def runner(args, **kw):
                row = f.run(args, **kw)
                if "--disassemble" in args:
                    f.paths["BEE"].write_bytes(b"replaced owned fixture")
                return row
            report = q.collect(f.app, f.policy, runner)
            self.assertEqual(report["collectionStatus"], "BLOCKED")
            self.assertEqual(report["reason"], "MODULE_CHANGED_DURING_COLLECTION:BEE")

    def test_truncated_and_failed_tools_block(self):
        for row in (output("", 0, False), output("", 1, True)):
            with self.subTest(row=row), tempfile.TemporaryDirectory() as td:
                f = Fixture(Path(td))
                self.assertEqual(q.collect(f.app, f.policy, lambda *a, **kw: row)["collectionStatus"], "BLOCKED")

    def test_candidate_limit_is_not_partial_success(self):
        with tempfile.TemporaryDirectory() as td, mock.patch.object(q, "MAX_LEADS", 1):
            f = Fixture(Path(td))
            self.assertEqual(q.collect(f.app, f.policy, f.run)["reason"], "CANDIDATE_LIMIT:BEE")

    def test_subprocess_success_error_and_encoding(self):
        for code, status in (("print('owned')", True), ("raise SystemExit(7)", False),
                             ("import os; os.write(1, b'\\xff')", False)):
            row = q.run_tool([sys.executable, "-c", code], timeout=5, max_bytes=1024)
            self.assertEqual(row["complete"], status, row)

    def test_subprocess_output_is_bounded_during_execution(self):
        row = q.run_tool([sys.executable, "-c", "import os; os.write(1, b'x' * 1000000)"],
                         timeout=5, max_bytes=100)
        self.assertEqual(row["reason"], "OUTPUT_LIMIT")
        self.assertEqual(row["bytes"], 100)
        self.assertFalse(row["complete"])

    def test_subprocess_timeout_including_closed_pipe(self):
        for code in ("import time; time.sleep(30)",
                     "import os,time; os.close(1); os.close(2); time.sleep(30)"):
            row = q.run_tool([sys.executable, "-c", code], timeout=0.1, max_bytes=1024)
            self.assertEqual(row["reason"], "TIMEOUT")
            self.assertFalse(row["complete"])

    def test_report_is_unique_and_hash_verified(self):
        with tempfile.TemporaryDirectory() as td:
            first = q.save_report({"collectionStatus": "BLOCKED"}, Path(td))
            second = q.save_report({"collectionStatus": "PASS"}, Path(td))
            self.assertNotEqual(first, second)
            self.assertEqual(json.loads(first.read_bytes())["collectionStatus"], "BLOCKED")
            self.assertEqual(first.with_name("SHA256.txt").read_text().split()[0], q.fingerprint(first))

    def test_non_macos_cli_refuses_without_host_commands(self):
        with tempfile.TemporaryDirectory() as td, mock.patch.object(q.platform, "system", return_value="Linux"), \
                mock.patch.object(q, "collect", side_effect=AssertionError("must not touch host")):
            self.assertEqual(q.main(["--app", "/not-an-ae-install", "--output", td]), 2)
            report = json.loads(next(Path(td).glob("*/report.json")).read_bytes())
            self.assertEqual(report["reason"], "MACOS_REQUIRED")
            self.assertIs(report["privateInvocationAllowed"], False)

    @unittest.skipUnless(sys.platform == "darwin", "requires Apple command-line tools; not an AE test")
    def test_real_apple_tools_on_owned_arm64_macho(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "owned.cpp"
            binary = Path(td) / "owned.dylib"
            source.write_text('extern "C" int fstr_queue_static_control(int x) { return x + 1; }\n')
            built = q.run_tool(["xcrun", "clang++", "-arch", "arm64", "-dynamiclib", "-O1",
                                str(source), "-o", str(binary)])
            self.assertTrue(built["complete"], built)
            symbols = q.run_tool(["xcrun", "nm", "-arch", "arm64", "-gU", str(binary)], max_bytes=q.MAX_NM)
            self.assertTrue(symbols["complete"], symbols)
            symbol = "_fstr_queue_static_control"
            address = q.text_symbols(symbols["text"])[symbol]
            result = q.run_tool(["xcrun", "llvm-objdump", "--macho", "--arch=arm64", "--disassemble",
                                 "--no-show-raw-insn", "--dis-symname", symbol, str(binary)])
            self.assertTrue(result["complete"], result)
            self.assertGreater(q.inspect_body(result["text"], symbol, address)["instructionCount"], 0)
            uid = q.run_tool(["xcrun", "dwarfdump", "--uuid", str(binary)])
            self.assertTrue(uid["complete"], uid)
            q.arm64_uuid(uid["text"])


if __name__ == "__main__":
    unittest.main()
