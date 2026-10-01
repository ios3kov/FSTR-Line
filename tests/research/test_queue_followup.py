"""Bounded follow-up collection on owned fixtures; never an Adobe runtime test."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from test_queue_static import Fixture, body, output, q

# Deliberately fabricated C names, NOT candidate Adobe declarations or ABIs.
QUEUE = "_BEE_ThreadedRenderUpdateQueue_Run_owned_fixture"
CONTEXT = "_BEE_Globals_GetProject_owned_fixture"


def add_candidates(f):
    f.symbols["BEE"][QUEUE] = 0x2000
    f.symbols["AfterFXLib"][CONTEXT] = 0x3000


class QueueFollowupTests(unittest.TestCase):
    def test_explicit_candidates_are_collected_in_addition_to_all_roots(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td)); add_candidates(f)
            report = q.collect(f.app, f.policy, f.run,
                               inspect_symbols=["BEE:" + QUEUE, "AfterFXLib:" + CONTEXT])
            self.assertEqual(report["collectionStatus"], "PASS", report)
            self.assertEqual(report["expectedBodyCount"], 9)
            for key, symbol in (("BEE", QUEUE), ("AfterFXLib", CONTEXT)):
                self.assertIn(symbol, report["requestedSymbols"][key])
                self.assertIn(symbol, report["modules"][key]["bodies"])
                self.assertTrue(set(q.REQUIRED[key]) <= set(report["modules"][key]["bodies"]))
            self.assertEqual(report["SYNC-001"], "NOT RUN")
            self.assertFalse(report["privateInvocationAllowed"])
            self.assertEqual(set(report["claims"].values()), {"UNPROVEN"})
            self.assertFalse(any("lldb" in a or "--attach" in a for a in f.calls))

    def test_default_does_not_disassemble_every_inventory_lead(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td)); add_candidates(f)
            report = q.collect(f.app, f.policy, f.run)
            self.assertEqual(report["collectionStatus"], "PASS", report)
            self.assertEqual(report["expectedBodyCount"], 7)
            self.assertNotIn(QUEUE, report["modules"]["BEE"]["bodies"])
            self.assertTrue(any(r["symbol"] == QUEUE for r in report["modules"]["BEE"]["inventory"]))

    def test_invalid_requests_refuse_before_tools_or_application_read(self):
        bad = [None, "BEE:" + QUEUE, [None], [123], ["BEE"], [":"], ["Other:" + QUEUE],
               ["BEE:--help"], ["BEE:0x1000"], ["BEE:_unrelated"],
               ["BEE:" + QUEUE + ",_other"], ["BEE:" + QUEUE + ":other"],
               ["BEE:" + QUEUE + "\n"], ["BEE:" + QUEUE + ";exit"],
               ["BEE:" + QUEUE + " value"], ["BEE:" + QUEUE + "\x00"],
               ["BEE:_" + "x" * 2048]]
        for values in bad:
            with self.subTest(values=values):
                runner = mock.Mock(side_effect=AssertionError("must not execute tools"))
                report = q.collect(Path("/not-an-install"), {}, runner, inspect_symbols=values)
                self.assertEqual(report["collectionStatus"], "BLOCKED")
                self.assertIn(report["reason"], ("INVALID_SYMBOL_SELECTION", "SYMBOL_OUTSIDE_RESEARCH_SCOPE"))
                runner.assert_not_called()

    def test_duplicate_requests_and_budget_are_not_silently_truncated(self):
        for values, reason in ((["BEE:" + QUEUE] * 2, "DUPLICATE_SYMBOL_SELECTION"),
                               (["BEE:" + QUEUE + str(i) for i in range(13)], "SYMBOL_SELECTION_LIMIT")):
            with self.subTest(reason=reason):
                report = q.collect(Path("/not-an-install"), {}, inspect_symbols=values)
                self.assertEqual(report["collectionStatus"], "BLOCKED")
                self.assertEqual(report["reason"], reason)
                self.assertEqual(report["commands"], [])

    def test_exact_selection_budget_collects_all_requests(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td))
            requests = []
            for i in range(12):
                symbol = QUEUE + str(i)
                f.symbols["BEE"][symbol] = 0x2000 + 16 * i
                requests.append("BEE:" + symbol)
            report = q.collect(f.app, f.policy, f.run, inspect_symbols=requests)
            self.assertEqual(report["collectionStatus"], "PASS", report)
            self.assertEqual(report["expectedBodyCount"], 19)
            self.assertEqual(sum(len(m["bodies"]) for m in report["modules"].values()), 19)

    def test_an_already_required_symbol_is_collected_once(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td))
            symbol = q.REQUIRED["AfterFXLib"][1]
            report = q.collect(f.app, f.policy, f.run, inspect_symbols=["AfterFXLib:" + symbol])
            self.assertEqual(report["collectionStatus"], "PASS", report)
            self.assertEqual(report["expectedBodyCount"], 7)
            self.assertEqual(sum("--dis-symname" in a and symbol in a for a in f.calls), 1)

    def test_missing_selected_symbol_in_either_module_blocks_before_any_body(self):
        for key, symbol in (("BEE", QUEUE), ("AfterFXLib", CONTEXT)):
            with self.subTest(module=key), tempfile.TemporaryDirectory() as td:
                f = Fixture(Path(td))
                report = q.collect(f.app, f.policy, f.run, inspect_symbols=[key + ":" + symbol])
                self.assertEqual(report["collectionStatus"], "BLOCKED", report)
                self.assertTrue(report["reason"].startswith("SELECTED_SYMBOL_MISSING:" + key))
                self.assertFalse(any("--disassemble" in a for a in f.calls))

    def test_unselected_module_still_has_to_pass_symbol_preflight(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td)); add_candidates(f)
            f.symbols["AfterFXLib"].pop(q.REQUIRED["AfterFXLib"][1])
            report = q.collect(f.app, f.policy, f.run, inspect_symbols=["BEE:" + QUEUE])
            self.assertEqual(report["collectionStatus"], "BLOCKED", report)
            self.assertTrue(report["reason"].startswith("REQUIRED_SYMBOL_MISSING:AfterFXLib"))
            self.assertFalse(any("--disassemble" in a for a in f.calls))

    def test_selected_body_failure_never_degrades_to_roots_only_pass(self):
        for kind in ("missing", "wrong-address", "failed", "limited"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as td:
                f = Fixture(Path(td)); add_candidates(f)
                def runner(args, **bounds):
                    if "--dis-symname" in args and CONTEXT in args:
                        if kind == "missing": return output("fixture:\n")
                        if kind == "wrong-address": return output(body(CONTEXT, 0x3004))
                        return output("", code=1 if kind == "failed" else 0,
                                      complete=kind != "limited")
                    return f.run(args, **bounds)
                report = q.collect(f.app, f.policy, runner, inspect_symbols=["AfterFXLib:" + CONTEXT])
                self.assertEqual(report["collectionStatus"], "BLOCKED", report)
                self.assertNotIn(CONTEXT, report["modules"]["AfterFXLib"]["bodies"])
                self.assertFalse(report["privateInvocationAllowed"])

    def test_selection_cannot_override_build_or_module_identity(self):
        for field in ("build", "hash", "uuid"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as td:
                f = Fixture(Path(td)); add_candidates(f)
                if field == "build": f.policy["aeBundleVersion"] = "wrong"
                if field == "hash": f.policy["modules"]["BEE"]["sha256"] = "0" * 64
                def runner(args, **bounds):
                    result = f.run(args, **bounds)
                    if field == "uuid" and args[1] == "dwarfdump":
                        return output("UUID: ffffffff-ffff-4fff-8fff-ffffffffffff (arm64) fixture\n")
                    return result
                report = q.collect(f.app, f.policy, runner, inspect_symbols=["BEE:" + QUEUE])
                self.assertEqual(report["collectionStatus"], "BLOCKED", report)
                self.assertFalse(any("nm" in a or "--disassemble" in a for a in f.calls))

    def test_replacement_while_collecting_selected_body_remains_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(Path(td)); add_candidates(f)
            def runner(args, **bounds):
                result = f.run(args, **bounds)
                if "--dis-symname" in args and QUEUE in args:
                    f.paths["BEE"].write_bytes(b"changed owned fixture")
                return result
            report = q.collect(f.app, f.policy, runner, inspect_symbols=["BEE:" + QUEUE])
            self.assertEqual(report["reason"], "MODULE_CHANGED_DURING_COLLECTION:BEE")
            self.assertEqual(report["collectionStatus"], "BLOCKED")

    def test_cli_passes_selection_and_saves_identity_bound_result(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); f = Fixture(root); add_candidates(f)
            policy = json.dumps(f.policy).encode()
            (root / "deep_targets.json").write_bytes(policy)
            original = q.collect
            def collect(app, config, **kwargs):
                return original(app, config, f.run, **kwargs)
            with mock.patch.object(q, "ROOT", root), mock.patch.object(q.platform, "system", return_value="Darwin"), \
                    mock.patch.object(q, "collect", side_effect=collect):
                code = q.main(["--app", str(f.app), "--output", str(root / "reports"),
                               "--inspect-symbol", "BEE:" + QUEUE,
                               "--inspect-symbol", "AfterFXLib:" + CONTEXT])
            self.assertEqual(code, 0)
            saved = next((root / "reports").glob("*/report.json"))
            report = json.loads(saved.read_bytes())
            self.assertEqual(report["expectedBodyCount"], 9)
            self.assertEqual(report["policySha256"], q.digest(policy))
            self.assertEqual(report["collectorSha256"], q.fingerprint(Path(q.__file__)))
            self.assertEqual(saved.with_name("SHA256.txt").read_text().split()[0], q.fingerprint(saved))

    @unittest.skipUnless(sys.platform == "darwin", "real Apple tools required; owned fixtures, not AE")
    def test_real_apple_tools_collect_extra_symbol_end_to_end(self):
        # The only substituted values are the policy and two synthetic roots.
        # nm, UUID discovery, hashing and all disassembly run on real owned dylibs.
        roots = {"BEE": ("_fstr_queue_root",), "AfterFXLib": ("_fstr_context_root",)}
        with tempfile.TemporaryDirectory() as td, mock.patch.object(q, "REQUIRED", roots):
            root = Path(td); f = Fixture(root)
            source = root / "owned.cpp"
            source.write_text('extern "C" int fstr_queue_root(int x) { return x + 1; }\n'
                              'extern "C" int fstr_context_root(int x) { return x + 2; }\n'
                              'extern "C" int BEE_ThreadedRenderUpdateQueue_Run_owned_fixture(int x) { return x + 3; }\n')
            result = q.run_tool(["xcrun", "clang++", "-arch", "arm64", "-dynamiclib", "-O1",
                                 str(source), "-o", str(f.paths["BEE"])])
            self.assertTrue(result["complete"], result)
            shutil.copyfile(f.paths["BEE"], f.paths["AfterFXLib"])
            for key, path in f.paths.items():
                uid = q.run_tool(["xcrun", "dwarfdump", "--uuid", str(path)])
                self.assertTrue(uid["complete"], uid)
                f.policy["modules"][key].update(sha256=q.fingerprint(path), uuid=q.arm64_uuid(uid["text"]))
            report = q.collect(f.app, f.policy, inspect_symbols=["BEE:" + QUEUE])
            self.assertEqual(report["collectionStatus"], "PASS", report)
            self.assertEqual(report["expectedBodyCount"], 3)
            self.assertIn(QUEUE, report["modules"]["BEE"]["bodies"])
            self.assertFalse(report["privateInvocationAllowed"])
            self.assertEqual(report["SYNC-001"], "NOT RUN")


if __name__ == "__main__":
    unittest.main()
