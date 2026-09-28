import importlib.util
import json
from pathlib import Path
import tempfile
import types
import unittest

MODULE = Path(__file__).resolve().parents[2] / 'research/ae-notifications/trace_callback.py'
spec = importlib.util.spec_from_file_location('trace_callback', MODULE)
trace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trace)
UID = '01234567-89ab-cdef-0123-456789abcdef'


def frame(pid=42, uid=UID):
    process = types.SimpleNamespace(GetProcessID=lambda: pid)
    thread = types.SimpleNamespace(GetProcess=lambda: process, GetThreadID=lambda: 7)
    module = types.SimpleNamespace(GetUUIDString=lambda: uid)
    address = types.SimpleNamespace(GetModule=lambda: module, GetFileAddress=lambda: 0x1234)
    return types.SimpleNamespace(GetThread=lambda: thread, GetPCAddress=lambda: address,
                                 GetFunctionName=lambda: 'FixtureOnly_NotAnAECandidate')


def location():
    bp = types.SimpleNamespace(GetID=lambda: 1)
    return types.SimpleNamespace(GetBreakpoint=lambda: bp, GetID=lambda: 1)


class TraceTests(unittest.TestCase):
    def tearDown(self):
        trace.stop_capture()

    def test_no_implicit_capture_or_resume(self):
        self.assertTrue(trace.on_breakpoint(frame(), location(), {}))

    def test_bound_identity_and_no_post_commit_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'trace.jsonl'
            trace.start_capture(path, 'fixture', 42, {UID: 'a' * 64}, max_events=1)
            self.assertFalse(trace.on_breakpoint(frame(), location(), {}))
            self.assertTrue(trace.on_breakpoint(frame(), location(), {}))
            trace.stop_capture()
            records = [json.loads(line) for line in path.read_text().splitlines()]
            hit = next(row for row in records if row['kind'] == 'candidate-hit')
            self.assertEqual(hit['commitPhase'], 'UNKNOWN')
            self.assertFalse(hit['isNotificationProven'])
            self.assertEqual(hit['unslidAddress'], '0x1234')
            self.assertTrue(any(row['kind'] == 'capture-limit' for row in records))
            self.assertEqual(records[-1]['SYNC-001'], 'NOT RUN')

    def test_wrong_pid_or_module_pauses(self):
        for pid, uid in [(99, UID), (42, 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')]:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'trace.jsonl'
                trace.start_capture(path, 'fixture', 42, {UID: 'a' * 64})
                self.assertTrue(trace.on_breakpoint(frame(pid, uid), location(), {}))
                trace.stop_capture()
                self.assertIn('capture-error', path.read_text())

    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'trace.jsonl'
            path.write_text('original')
            with self.assertRaises(FileExistsError):
                trace.start_capture(path, 'fixture', 42, {UID: 'a' * 64})
            self.assertEqual(path.read_text(), 'original')

    def test_validation_precedes_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'trace.jsonl'
            with self.assertRaises(ValueError):
                trace.start_capture(path, 'fixture', 42, {UID: 'bad hash'})
            self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main()
