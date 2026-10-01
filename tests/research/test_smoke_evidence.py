"""Diagnostics controls on owned files/processes and fake SB objects. NOT AE."""
import hashlib
import importlib.util
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest import mock

import smoke_evidence as e

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / 'research/ae-notifications'


def load_controller():
    spec = importlib.util.spec_from_file_location('stage_control', RESEARCH / 'runtime_control.py')
    module = importlib.util.module_from_spec(spec)
    error = types.SimpleNamespace(Fail=lambda: False)
    fake_lldb = types.SimpleNamespace(SBError=lambda: error, eStateRunning=6,
                                     eStateExited=10, eStateCrashed=8, eStateDetached=9,
                                     eStateStopped=5, eStateStepping=7)
    logger = types.SimpleNamespace(start_capture=lambda *a, **kw: None,
                                  mark_phase=lambda *a: None, stop_capture=lambda: None,
                                  prepare_shutdown=lambda: None)
    sys.path.insert(0, str(RESEARCH))
    try:
        with mock.patch.dict(sys.modules, {'lldb': fake_lldb, 'trace_callback': logger}):
            spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


class EvidenceTests(unittest.TestCase):
    def test_unique_files_and_hashes_keep_fail(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            work = root / 'work'; work.mkdir()
            (work / 'result.json').write_text('{"status":"PASS"}')
            first = e.save_evidence(work, root / 'out', {'status': 'FAIL', 'errorType': 'TimeoutExpired'})
            second = e.save_evidence(work, root / 'out', {'status': 'PASS'})
            report = json.loads(first.read_text())
            self.assertEqual(report['status'], 'FAIL')
            self.assertEqual(report['SYNC-001'], 'NOT RUN')
            self.assertNotEqual(first, second)
            self.assertEqual(first.with_name('SHA256.txt').read_text().split()[0], hashlib.sha256(first.read_bytes()).hexdigest())
            self.assertEqual(set(report['files']), set(e.FILES))
            self.assertFalse(report['files']['trace.jsonl']['complete'])

    def test_oversize_input_is_bounded_and_flagged(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); work = root / 'work'; work.mkdir()
            (work / 'lldb.log').write_bytes(b'x' * (e.MAX_LOG + 100))
            path = e.save_evidence(work, root / 'out', {'status': 'FAIL'})
            row = json.loads(path.read_text())['files']['lldb.log']
            self.assertFalse(row['complete'])
            self.assertEqual(len(row['text']), e.MAX_LOG)

    def test_symlink_and_fifo_not_read(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); work = root / 'work'; work.mkdir()
            outside = root / 'private'; outside.write_text('DO-NOT-COPY')
            (work / 'lldb.log').symlink_to(outside)
            os.mkfifo(work / 'ack.jsonl')
            path = e.save_evidence(work, root / 'out', {'status': 'FAIL'})
            self.assertNotIn('DO-NOT-COPY', path.read_text())
            rows = json.loads(path.read_text())['files']
            self.assertFalse(rows['ack.jsonl']['complete'])
            self.assertFalse(rows['lldb.log']['complete'])

    def test_redacts_paths_before_json_encoding(self):
        with tempfile.TemporaryDirectory(prefix='owned-Юникод-') as td:
            root = Path(td); work = root / 'work'; work.mkdir()
            (work / 'plan.json').write_text(str(work) + '\n' + str(Path.home()))
            path = e.save_evidence(work, root / 'out', {'status': 'FAIL'})
            text = json.loads(path.read_text())['files']['plan.json']['text']
            self.assertEqual(text, '<FIXTURE>\n<HOME>')

    def test_child_log_drains_but_never_grows_past_limit(self):
        with tempfile.TemporaryDirectory() as td:
            p = subprocess.Popen([sys.executable, '-c', "import os; os.write(1, b'x'*1000000)"], stdout=subprocess.PIPE)
            log = e.BoundedLog(p.stdout, Path(td) / 'lldb.log')
            try:
                p.wait(timeout=5)
                result = log.finish()
                self.assertTrue(result['readerStopped'])
                self.assertTrue(result['truncated'])
                self.assertFalse(result['complete'])
                self.assertEqual((Path(td) / 'lldb.log').stat().st_size, e.MAX_LOG)
            finally:
                e.reap_owned(p)

    def test_child_log_normal_exit(self):
        with tempfile.TemporaryDirectory() as td:
            p = subprocess.Popen([sys.executable, '-c', "print('owned')"], stdout=subprocess.PIPE)
            log = e.BoundedLog(p.stdout, Path(td) / 'lldb.log')
            try:
                p.wait(timeout=5)
                self.assertTrue(log.finish()['complete'])
                self.assertEqual((Path(td) / 'lldb.log').read_text(), 'owned\n')
            finally:
                e.reap_owned(p)

    def test_reap_stopped_owned_child_and_preserve_other_child(self):
        code = 'import os,signal,time; os.kill(os.getpid(),signal.SIGSTOP); time.sleep(30)'
        p = subprocess.Popen([sys.executable, '-c', code])
        other = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
        try:
            # Deterministic rendezvous: wait for the test child's stopped state.
            _, status = os.waitpid(p.pid, os.WUNTRACED)
            self.assertTrue(os.WIFSTOPPED(status))
            row = e.reap_owned(p, resume=True)
            self.assertTrue(row['reaped'], row)
            self.assertIsNone(other.poll())
        finally:
            e.reap_owned(p, resume=True); e.reap_owned(other)

    def test_cleanup_failure_is_explicit(self):
        p = mock.Mock()
        p.poll.return_value = None
        p.terminate.side_effect = PermissionError()
        self.assertFalse(e.reap_owned(p)['reaped'])

    def test_kill_fallback_is_bounded(self):
        p = mock.Mock()
        p.poll.return_value = None
        p.wait.side_effect = [subprocess.TimeoutExpired('owned', 2), -9]
        row = e.reap_owned(p)
        self.assertTrue(row['reaped'])
        p.kill.assert_called_once()
        self.assertEqual(row['actions'], ['terminate', 'kill'])


class StageTests(unittest.TestCase):
    def test_stage_is_opt_in(self):
        c = load_controller()
        with mock.patch.object(c, '_ack', side_effect=AssertionError()):
            c._stage({}, {}, 'stop-begin')

    def test_stage_io_failure_cannot_prevent_cleanup(self):
        c = load_controller(); result = {}
        with mock.patch.object(c, '_ack', side_effect=OSError()):
            for _ in range(70):
                c._stage({'diagnosticStages': True, 'ackPath': 'unused'}, result, 'detach-begin')
        self.assertEqual(len(result['diagnosticErrors']), 64)

    def exercise(self, *, stop_error=False, detach_error=False, setup_error=False, kind="finish"):
        c = load_controller()
        success = types.SimpleNamespace(Fail=lambda: False)
        process = mock.Mock()
        process.IsValid.return_value = True
        process.GetState.side_effect = [c.lldb.eStateRunning, c.lldb.eStateStopped]
        process.Continue.return_value = success
        process.SendAsyncInterrupt.side_effect = RuntimeError('owned interrupt failure') if stop_error else None
        process.Stop.side_effect = AssertionError('Synchronous Stop must not be used')
        process.Detach.return_value = types.SimpleNamespace(Fail=lambda: detach_error)
        if setup_error:
            c.trace_callback.start_capture = mock.Mock(side_effect=RuntimeError("owned setup failure"))
        target = mock.Mock()
        target.AttachToProcessWithID.return_value = process
        debugger = mock.Mock(); debugger.CreateTarget.return_value = target
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            plan = {'pid': 1234, 'runId': 'owned', 'executable': 'owned', 'modules': [], 'breakpoints': [],
                    'durationSeconds': 10, 'diagnosticStages': True,
                    **{key: str(t / name) for key, name in (
                        ('controlPath', 'control.jsonl'), ('ackPath', 'ack.jsonl'),
                        ('tracePath', 'trace.jsonl'), ('resultPath', 'result.json'))}}
            (t / 'plan.json').write_text(json.dumps(plan))
            (t / 'control.jsonl').write_text(json.dumps({'kind': kind, 'sequence': 1}) + '\n')
            c.run(debugger, str(t / 'plan.json'))
            rows = [json.loads(line) for line in (t / 'ack.jsonl').read_text().splitlines()]
            result = json.loads((t / 'result.json').read_text())
        return [r['stage'] for r in rows if r['kind'] == 'controller-stage'], result, process, debugger

    def test_success_records_shutdown_in_order(self):
        stages, result, process, debugger = self.exercise()
        self.assertEqual(result['status'], 'PASS')
        expected = ['shutdown-interrupt-begin', 'shutdown-interrupt-sent', 'shutdown-stop-confirmed',
                    'detach-begin', 'detach-end', 'capture-close-begin', 'capture-close-end',
                    'target-retained-for-debugger-exit', 'controller-return']
        self.assertEqual([x for x in stages if x in expected], expected)
        process.Detach.assert_called_once_with(False); debugger.DeleteTarget.assert_not_called()

    def test_interrupt_failure_keeps_fail_without_blocking_fallback(self):
        stages, result, process, debugger = self.exercise(stop_error=True)
        self.assertEqual(result['status'], 'FAIL')
        self.assertIn('shutdown-interrupt-begin', stages)
        self.assertNotIn('shutdown-stop-confirmed', stages)
        self.assertIn('confirmed stop', result['detachError'])
        self.assertFalse(result['detached'])
        self.assertEqual(stages[-1], 'controller-return')
        process.SendAsyncInterrupt.assert_called_once()
        process.Stop.assert_not_called(); process.Detach.assert_not_called()
        debugger.DeleteTarget.assert_not_called()

    def test_setup_failure_uses_async_recovery_and_retains_fail(self):
        stages, result, process, debugger = self.exercise(setup_error=True)
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(result['detached'])
        self.assertIn('recovery-stop-confirmed', stages)
        process.SendAsyncInterrupt.assert_called_once()
        process.Stop.assert_not_called()
        process.Detach.assert_called_once_with(False)

    def test_failed_detach_is_not_retried_or_marked_successful(self):
        stages, result, process, debugger = self.exercise(detach_error=True)
        self.assertEqual(result['status'], 'FAIL')
        self.assertFalse(result['detached'])
        self.assertIn('not retried', result['detachError'])
        process.Detach.assert_called_once_with(False)
        self.assertNotIn('recovery-detach-begin', stages)

    def test_abort_still_stops_and_detaches_without_becoming_pass(self):
        stages, result, process, debugger = self.exercise(kind='abort')
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['stage'], 'aborted')
        self.assertTrue(result['detached'])
        process.Stop.assert_not_called()
        process.Detach.assert_called_once_with(False)

    def test_reentry_refused_before_creating_another_target(self):
        c = load_controller()
        c._run_started = True
        debugger = mock.Mock()
        with self.assertRaisesRegex(RuntimeError, 'fresh dedicated'):
            c.run(debugger, 'not-read')
        debugger.CreateTarget.assert_not_called()


if __name__ == '__main__':
    unittest.main()
