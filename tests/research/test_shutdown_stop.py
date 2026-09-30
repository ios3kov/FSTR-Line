"""Shutdown API models, actual logger and owned-child liveness. Never Adobe AE."""
import importlib.util
import json
import os
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from test_smoke_evidence import load_controller, RESEARCH
from fixture_liveness import require_progress, _counter
from smoke_evidence import reap_owned


class StopTests(unittest.TestCase):
    def exercise(self, states, *, timeout=False, interrupt_error=False):
        c = load_controller()
        p = mock.Mock()
        p.GetState.side_effect = states
        p.Stop.side_effect = AssertionError('Do not use synchronous Stop')
        if interrupt_error:
            p.SendAsyncInterrupt.side_effect = RuntimeError('interrupt rejected')
        d = mock.Mock()
        result = {}
        c.trace_callback.prepare_shutdown = mock.Mock()
        with mock.patch.object(c.time, 'sleep'), mock.patch.object(c.time, 'monotonic') as clock:
            clock.side_effect = [0, 6] if timeout else None
            clock.return_value = 0
            try:
                c._pause_for_detach(d, p, {}, result)
                error = None
            except RuntimeError as exc:
                error = exc
        d.SetAsync.assert_called_once_with(True)
        c.trace_callback.prepare_shutdown.assert_called_once()
        p.Stop.assert_not_called()
        return result, p, error

    def test_running_and_stepping_require_observed_stop(self):
        for states in ([6, 6, 5], [7, 7, 5]):
            with self.subTest(states=states):
                result, p, error = self.exercise(states)
                self.assertIsNone(error)
                self.assertTrue(result['stopConfirmed'])
                p.SendAsyncInterrupt.assert_called_once()

    def test_already_stopped_needs_no_interrupt(self):
        result, p, error = self.exercise([5])
        self.assertIsNone(error)
        self.assertTrue(result['stopConfirmed'])
        p.SendAsyncInterrupt.assert_not_called()

    def test_timeout_does_not_claim_stop(self):
        result, p, error = self.exercise([6], timeout=True)
        self.assertIn('Timed out', str(error))
        self.assertNotIn('stopConfirmed', result)
        p.SendAsyncInterrupt.assert_called_once()

    def test_terminal_or_unknown_initial_state_is_rejected(self):
        for state in (0, 1, 3, 8, 9, 10):
            with self.subTest(state=state):
                result, p, error = self.exercise([state])
                self.assertIsNotNone(error)
                self.assertNotIn('stopConfirmed', result)
                p.SendAsyncInterrupt.assert_not_called()

    def test_exit_crash_or_detach_while_stopping_is_not_success(self):
        for state in (0, 8, 9, 10):
            with self.subTest(state=state):
                result, p, error = self.exercise([6, state])
                self.assertIsNotNone(error)
                self.assertNotIn('stopConfirmed', result)

    def test_interrupt_error_is_not_a_stop_receipt(self):
        result, p, error = self.exercise([6], interrupt_error=True)
        self.assertIsNotNone(error)
        self.assertNotIn('stopConfirmed', result)

    def test_controller_contains_no_blocking_stop_or_target_kill(self):
        import ast
        tree = ast.parse((RESEARCH / 'runtime_control.py').read_text())
        calls = [n.func.attr for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
        for forbidden in ('Stop', 'Kill', 'Destroy', 'EvaluateExpression'):
            self.assertNotIn(forbidden, calls)


class LoggerShutdownTests(unittest.TestCase):
    def test_late_callback_pauses_without_touching_sb_objects(self):
        spec = importlib.util.spec_from_file_location('shutdown_logger', RESEARCH / 'trace_callback.py')
        logger = importlib.util.module_from_spec(spec); spec.loader.exec_module(logger)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'trace.jsonl'
            logger.prepare_shutdown()  # No active capture is safe and has no side effects.
            logger.start_capture(path, 'owned', 123, {'00000000-0000-0000-0000-000000000001': 'a'*64})
            try:
                logger.prepare_shutdown()
                logger.prepare_shutdown()
                # No frame/breakpoint API may be called after shutdown was requested.
                self.assertTrue(logger.on_breakpoint(None, None, None))
            finally:
                logger.stop_capture()
            rows = [json.loads(x) for x in path.read_text().splitlines()]
            self.assertEqual([r['kind'] for r in rows], ['capture-start', 'capture-end'])
            self.assertEqual(rows[-1]['hits'], 0)
            self.assertEqual(rows[-1]['SYNC-001'], 'NOT RUN')


class FixtureLivenessTests(unittest.TestCase):
    def test_target_written_counter_advances_without_signals(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'counter'
            code = ('import os,sys,time; f=os.open(sys.argv[1],os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600); '
                    '\nfor i in range(1000):\n os.pwrite(f,i.to_bytes(8,"little"),0); time.sleep(.01)')
            p = subprocess.Popen([sys.executable, '-c', code, str(path)])
            try:
                row = require_progress(p, path)
                self.assertGreater(row['after'], row['before'])
                self.assertFalse(row['resumedByTest'])
            finally:
                reap_owned(p)

    def test_dead_child_is_rejected_despite_old_counter(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'counter'; path.write_bytes((1).to_bytes(8, 'little'))
            p = subprocess.Popen([sys.executable, '-c', 'pass'])
            p.wait(timeout=3)
            with self.assertRaisesRegex(RuntimeError, 'exited'):
                require_progress(p, path)

    def test_stopped_owned_child_is_not_treated_as_alive_and_running(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'counter'; path.write_bytes((1).to_bytes(8, 'little'))
            p = subprocess.Popen([sys.executable, '-c', 'import os,signal; os.kill(os.getpid(),signal.SIGSTOP)'])
            try:
                _, status = os.waitpid(p.pid, os.WUNTRACED)
                self.assertTrue(os.WIFSTOPPED(status))
                with self.assertRaisesRegex(RuntimeError, 'did not progress'):
                    require_progress(p, path, timeout=.1)
                self.assertIsNone(p.poll())
            finally:
                reap_owned(p, resume=True)

    def test_malformed_and_nonregular_counter_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); path = root / 'counter'
            path.write_bytes(b'x'*9)
            with self.assertRaises(ValueError): _counter(path)
            link = root / 'link'; link.symlink_to(path)
            with self.assertRaises(OSError): _counter(link)
            fifo = root / 'fifo'; os.mkfifo(fifo)
            with self.assertRaises(ValueError): _counter(fifo)


if __name__ == '__main__':
    unittest.main()
