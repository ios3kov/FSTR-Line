"""Actual parent entry point with controlled transport; no Adobe process or calls."""
import importlib.util
import json
import os
import signal
import sys
import time
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('parent_exit_probe', ROOT / 'research/ae-notifications/runtime_probe.py')
REAL_POPEN = subprocess.Popen
p = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p)


class Child:
    """A debugger-process control, not a model of After Effects."""
    def __init__(self, code=0, timeout=False):
        self.pid = 90002
        self.code = code
        self.timeout = timeout
        self.returncode = None
        self.terminated = False
        self.killed = False
        self.waits = []

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        self.waits.append(timeout)
        if self.timeout and not self.terminated:
            raise subprocess.TimeoutExpired('owned-lldb-control', timeout)
        self.returncode = self.code
        return self.returncode

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True


class RuntimeParentExitTests(unittest.TestCase):
    def run_session(self, root, child, *, ready_error=None, result=None):
        session = root / 'session'
        def launched(*args, **kwargs):
            payload = {'status': 'PASS', 'stage': 'complete', 'detached': True, 'pid': 90001}
            if result is not None:
                payload = result
            if result == 'missing':
                pass
            elif result == 'symlink':
                (root / 'outside.json').write_text(json.dumps(payload))
                (session / 'result.json').symlink_to(root / 'outside.json')
            elif result == 'malformed':
                (session / 'result.json').write_text('{broken')
            elif result == 'oversized':
                (session / 'result.json').write_text(' ' * 65537)
            else:
                (session / 'result.json').write_text(json.dumps(payload))
            return child
        candidates = {'breakpoints': [], 'durationSeconds': 1, 'aeBundleId': 'org.fstr.fixture',
                      'attachReadyTimeoutSeconds': 1, 'shutdownTimeoutSeconds': 1}
        with mock.patch.object(p.subprocess, 'Popen', side_effect=launched), \
             mock.patch.object(p.runtime_protocol, 'wait_for_record', side_effect=ready_error), \
             mock.patch.object(p.runtime_protocol, 'send_finish'), \
             mock.patch.object(p.runtime_protocol, 'send_abort'), mock.patch('builtins.print'):
            return p.run_observer_session(root / 'owned-fixture', 90001, [], candidates, [],
                                          root, 'session', root / 'evidence.jsonl')

    def test_nonzero_debugger_exit_rejects_controller_pass(self):
        for code in (7, -11):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as td:
                with self.assertRaises(p.Blocked):
                    self.run_session(Path(td), Child(code=code))

    def test_shutdown_timeout_cannot_become_pass_after_zero_exit(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(p.Blocked):
                self.run_session(Path(td), Child(code=0, timeout=True))

    def test_ready_failure_still_reaps_debugger(self):
        with tempfile.TemporaryDirectory() as td:
            child = Child(timeout=True)
            with self.assertRaises(TimeoutError):
                self.run_session(Path(td), child, ready_error=TimeoutError('fixture ready deadline'))
            self.assertIsNotNone(child.returncode)


    def test_normal_exit_and_matching_detached_result_pass(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = self.run_session(root, Child())
            self.assertEqual(result['status'], 'PASS')
            ledger = json.loads((root / 'session/observer-parent.json').read_text())
            self.assertEqual(ledger['status'], 'PASS')
            self.assertTrue(p._clean_debugger_exit(ledger))
            self.assertEqual(ledger['controllerResultSha256'], p.sha256(root / 'session/result.json'))
            self.assertEqual(ledger['planSha256'], p.sha256(root / 'session/plan.json'))

    def test_rejected_controller_results_and_unsafe_files(self):
        good = {'status': 'PASS', 'stage': 'complete', 'detached': True, 'pid': 90001}
        for result in ('missing', 'malformed', 'oversized', 'symlink', [],
                       {**good, 'pid': 42}, {**good, 'pid': '90001'},
                       {**good, 'detached': 'yes'}, {**good, 'detached': False},
                       {**good, 'stage': 'aborted'}, {**good, 'status': 'FAIL'}):
            with self.subTest(result=result), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                with self.assertRaises(p.Blocked):
                    self.run_session(root, Child(), result=result)
                ledger = json.loads((root / 'session/observer-parent.json').read_text())
                self.assertEqual(ledger['status'], 'BLOCKED')
                self.assertFalse(ledger['resumeEligible'])

    def test_original_interrupt_is_preserved_and_clean_abort_is_resumable(self):
        aborted = {'status': 'BLOCKED', 'stage': 'aborted', 'detached': True, 'pid': 90001}
        for failure in (KeyboardInterrupt(), EOFError(), TimeoutError('fixture')):
            with self.subTest(error=type(failure).__name__), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                with self.assertRaises(type(failure)):
                    self.run_session(root, Child(), ready_error=failure, result=aborted)
                ledger = json.loads((root / 'session/observer-parent.json').read_text())
                self.assertEqual(ledger['resumeEligible'], isinstance(failure, (KeyboardInterrupt, EOFError)))
                self.assertEqual(ledger['status'], 'BLOCKED')

    def test_ready_failure_does_not_rewrite_controller_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaises(TimeoutError):
                self.run_session(root, Child(timeout=True), ready_error=TimeoutError())
            self.assertEqual(json.loads((root / 'session/result.json').read_text())['status'], 'PASS')
            ledger = json.loads((root / 'session/observer-parent.json').read_text())
            self.assertEqual(ledger['status'], 'BLOCKED')
            self.assertTrue(ledger['shutdownTimedOut'])
            self.assertFalse(ledger['resumeEligible'])

    def test_cleanup_error_and_unreaped_child_cannot_pass(self):
        child = Child(timeout=True)
        child.wait = mock.Mock(side_effect=subprocess.TimeoutExpired('owned', 1))
        outcome = p._wait_debugger_exit(child, 1)
        self.assertFalse(p._clean_debugger_exit(outcome))
        self.assertTrue(child.terminated)
        self.assertTrue(child.killed)
        self.assertFalse(outcome['debuggerReaped'])
        self.assertEqual(child.wait.call_count, 3)

    def test_bool_exit_code_is_not_integer_zero(self):
        with tempfile.TemporaryDirectory() as td, self.assertRaises(p.Blocked):
            self.run_session(Path(td), Child(code=False))

    def test_invalid_wait_bounds_refuse_before_launch(self):
        for key in ('attachReadyTimeoutSeconds', 'ackTimeoutSeconds', 'shutdownTimeoutSeconds'):
            for value in (None, 'bad', False, 0, -1, 601):
                with self.subTest(key=key, value=value), tempfile.TemporaryDirectory() as td:
                    root = Path(td)
                    with mock.patch.object(p.subprocess, 'Popen') as launched, self.assertRaises(p.Blocked):
                        p.run_observer_session(root/'owned', 90001, [], {key:value}, [], root,
                                               'session', root/'evidence.jsonl')
                    launched.assert_not_called()

    def test_launch_failure_retains_failure_without_claiming_reaped(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            candidates = {'breakpoints':[], 'durationSeconds':1}
            with mock.patch.object(p.subprocess, 'Popen', side_effect=OSError('fixture unavailable')):
                with self.assertRaises(OSError):
                    p.run_observer_session(root/'owned', 90001, [], candidates, [], root,
                                           'session', root/'evidence.jsonl')
            ledger = json.loads((root/'session/observer-parent.json').read_text())
            self.assertEqual(ledger['status'], 'BLOCKED')
            self.assertFalse(ledger['debuggerReaped'])
            self.assertEqual(ledger['sessionError'], 'OSError')

    def test_existing_session_is_not_overwritten_or_executed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'session').mkdir()
            old = root / 'session/result.json'
            old.write_text('preserved')
            with mock.patch.object(p.subprocess, 'Popen') as launched, self.assertRaises(FileExistsError):
                self.run_session(root, Child())
            launched.assert_not_called()
            self.assertEqual(old.read_text(), 'preserved')


# This is a separate, clearly labelled fake debugger process. It never runs LLDB
# or reads a project. Real pipe/file IPC and OS exit behaviour exercise the parent.
CHILD_SCRIPT = r"""
import json, os, signal, sys, time
from pathlib import Path
plan_path, mode = sys.argv[1:]
plan = json.loads(Path(plan_path).read_text())
if mode == 'ready-timeout':
    time.sleep(30)
    raise SystemExit(99)
Path(plan['ackPath']).write_text(json.dumps({'kind':'ready','sequence':0})+'\n')
while True:
    rows = Path(plan['controlPath']).read_text().splitlines()
    if rows and json.loads(rows[-1])['kind'] == 'finish':
        break
    time.sleep(.01)
Path(plan['resultPath']).write_text(json.dumps({
    'pid':plan['pid'],'status':'PASS','stage':'complete','detached':True}))
if mode == 'hang-zero':
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    time.sleep(30)
if mode == 'signal':
    os.kill(os.getpid(), signal.SIGTERM)
raise SystemExit(7 if mode == 'nonzero' else 0)
"""


class RealChildExitTests(unittest.TestCase):
    def test_actual_parent_with_owned_child_and_real_file_ipc(self):
        for mode in ('ok', 'nonzero', 'signal', 'hang-zero', 'ready-timeout'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(prefix='fstr-parent-') as td:
                root = Path(td) / 'Кириллица spaced'
                root.mkdir()
                made = []
                def launch(_args, **kwargs):
                    proc = REAL_POPEN([sys.executable, '-c', CHILD_SCRIPT,
                                       str(root / 'session/plan.json'), mode], **kwargs)
                    made.append(proc)
                    return proc
                candidates = {'breakpoints': [], 'durationSeconds': 1,
                              'aeBundleId': 'org.fstr.fixture', 'shutdownTimeoutSeconds': 1,
                              'attachReadyTimeoutSeconds': 1}
                try:
                    with mock.patch.object(p.subprocess, 'Popen', side_effect=launch), \
                         mock.patch('builtins.print'):
                        call = lambda: p.run_observer_session(root / 'owned', 90001, [], candidates,
                                                               [], root, 'session', root / 'evidence.jsonl')
                        if mode == 'ok':
                            self.assertEqual(call()['status'], 'PASS')
                        else:
                            with self.assertRaises((p.Blocked, TimeoutError)):
                                call()
                    ledger = json.loads((root / 'session/observer-parent.json').read_text())
                    self.assertEqual(ledger['status'], 'PASS' if mode == 'ok' else 'BLOCKED')
                    self.assertTrue(ledger['debuggerReaped'])
                    self.assertIsNotNone(made[0].poll())
                    if mode == 'hang-zero':
                        self.assertEqual(ledger['debuggerExitCode'], 0)
                        self.assertTrue(ledger['shutdownTimedOut'])
                finally:
                    for proc in made:
                        if proc.poll() is None:
                            proc.kill()
                        proc.wait(timeout=3)

    def test_term_ignoring_owned_child_is_killed_and_reaped(self):
        with tempfile.TemporaryDirectory() as td:
            ready = Path(td) / 'ready'
            script = "import signal,time;from pathlib import Path;signal.signal(signal.SIGTERM,signal.SIG_IGN);Path(%r).touch();time.sleep(30)" % str(ready)
            proc = REAL_POPEN([sys.executable, '-c', script])
            try:
                deadline = time.monotonic() + 3
                while not ready.exists() and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertTrue(ready.exists())
                result = p._wait_debugger_exit(proc, .05)
                self.assertTrue(result['shutdownTimedOut'])
                self.assertTrue(result['debuggerReaped'])
                self.assertEqual(result['debuggerExitCode'], -signal.SIGKILL)
                self.assertFalse(p._clean_debugger_exit(result))
            finally:
                if proc.poll() is None:
                    proc.kill()
                proc.wait(timeout=3)


class ResumeExitTests(unittest.TestCase):
    def test_resume_requires_correlated_unmodified_parent_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old = root / 'fstr-final-owned'
            session = old / 'pre-restart'
            session.mkdir(parents=True)
            binary = root / 'owned'
            binary.touch()
            candidates = {'breakpoints': [], 'preRestart': [{'label':'a'}, {'label':'b'}]}
            (old / 'evidence.jsonl').write_text('{"kind":"snapshot-after","session":"pre-restart","phase":"a"}\n')
            (session / 'plan.json').write_text(json.dumps({'runId':'owned','pid':42,
                'executable':str(binary),'breakpoints':[]}))
            (session / 'result.json').write_text(json.dumps({'pid':42,'status':'BLOCKED','stage':'aborted','detached':True}))
            good = {'runId':'owned','planSha256':p.sha256(session / 'plan.json'),
                    'controllerResultSha256':p.sha256(session / 'result.json'),
                    'resumeEligible':True,'debuggerExitCode':0,'debuggerReaped':True,
                    'shutdownTimedOut':False,'forcedTermination':False,'cleanupErrors':[]}
            for field, value in (('debuggerExitCode', -11), ('shutdownTimedOut', True),
                                  ('forcedTermination', True), ('debuggerReaped', False),
                                  ('runId', 'other'), ('planSha256', 'bad'),
                                  ('controllerResultSha256', 'bad'), ('resumeEligible', False)):
                (session / 'observer-parent.json').write_text(json.dumps({**good,field:value}))
                self.assertIsNone(p.find_resume_candidate(root,binary,42,candidates), field)
            (session / 'observer-parent.json').write_text(json.dumps(good))
            self.assertIsNotNone(p.find_resume_candidate(root,binary,42,candidates))
            (session / 'result.json').write_text('{}')
            self.assertIsNone(p.find_resume_candidate(root,binary,42,candidates))


if __name__ == '__main__':
    unittest.main()
