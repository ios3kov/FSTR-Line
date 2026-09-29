import importlib.util
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("completion_preflight", ROOT / "research/ae-notifications/completion_preflight.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class CompletionPreflightTests(unittest.TestCase):
    def test_positive_identity_never_authorizes_attach(self):
        with mock.patch.object(p.platform, "system", return_value="Darwin"), \
             mock.patch.object(p.platform, "machine", return_value="arm64"), \
             mock.patch.object(p.context_probe, "exact_identity", return_value=(Path("/fixture"), Path("/fixture/ae"), {})), \
             mock.patch.object(p.context_probe, "find_pid", return_value=42), \
             mock.patch.object(p.deep_static, "verify_module", return_value=(Path("/fixture/bee"), {"status":"PASS"})):
            report = p.preflight(Path("/fixture"), 42)
        self.assertEqual(report["status"], "PASS")
        self.assertFalse(report["attachAllowed"])
        self.assertEqual(report["projectOwnership"], "UNVERIFIED")
        self.assertEqual(report["SYNC-001"], "NOT RUN")

    def test_pid_mismatch_change_and_module_mismatch_refuse(self):
        for pids, module in (([43], Path("/fixture/bee")), ([42,43], Path("/fixture/bee")), ([42], None)):
            with self.subTest(pids=pids, module=module), \
                 mock.patch.object(p.platform, "system", return_value="Darwin"), \
                 mock.patch.object(p.platform, "machine", return_value="arm64"), \
                 mock.patch.object(p.context_probe, "exact_identity", return_value=(Path("/fixture"), Path("/fixture/ae"), {})), \
                 mock.patch.object(p.context_probe, "find_pid", side_effect=pids), \
                 mock.patch.object(p.deep_static, "verify_module", return_value=(module, {})):
                with self.assertRaises(ValueError): p.preflight(Path("/fixture"),42)

    def test_invalid_pid_and_platform_refuse_before_identity(self):
        with mock.patch.object(p.context_probe, "exact_identity") as identity:
            for pid in (0,-1,True,"42"):
                with self.assertRaises(ValueError): p.preflight(Path("/fixture"),pid)
            with mock.patch.object(p.platform,"system",return_value="Linux"):
                with self.assertRaises(ValueError): p.preflight(Path("/fixture"),42)
            identity.assert_not_called()


if __name__ == "__main__": unittest.main()
