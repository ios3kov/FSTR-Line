"""Offline evidence controls; no Adobe process, ABI or delivery is exercised."""
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('matrix_integrity_analyzer', ROOT / 'research/ae-notifications/analyze_runtime_matrix.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def encoded(value):
    return (json.dumps(value) + '\n').encode()


def fixture():
    """Synthetic complete captures, not a claim of AE execution."""
    members = {}
    members['summary.json'] = encoded({'status': 'PASS', 'sessions': ['pre-restart', 'post-restart'],
                                      'collectorBuild': {'sourceCommit': 'a' * 40}})
    evidence = [{'kind': 'restart-observed', 'pidChanged': True, 'oldPid': 41, 'newPid': 42}]
    for session, pid, phases in (
        ('pre-restart', 41, ['native-timing', 'native-comp-switch', 'extendscript-origin']),
        ('post-restart', 42, ['restart-extendscript']),
    ):
        run = 'runtime_' + session.replace('-', '_')
        rows = [{'kind': 'capture-start'}, {'kind': 'phase', 'label': 'attach-verified'}]
        hits = 0
        for phase in phases:
            rows += [{'kind': 'phase', 'label': phase + '-start'},
                     {'kind': 'candidate-hit', 'label': 'process-project-changes', 'pid': pid,
                      'source': 'lldb-breakpoint', 'commitPhase': 'UNKNOWN', 'isNotificationProven': False},
                     {'kind': 'phase', 'label': phase + '-done'}]
            hits += 1
            if 'extendscript' in phase:
                evidence.append({'kind': 'script-result', 'session': session, 'phase': phase,
                                 'result': {'ok': True, 'timedOut': False, 'returnCode': 0}})
        rows += [{'kind': 'phase', 'label': 'capture-finished'}, {'kind': 'capture-end', 'hits': hits}]
        for i, row in enumerate(rows, 1):
            row.update(testRunId=run, sequence=i, monotonicNs=i * 10)
        result = encoded({'status': 'PASS', 'stage': 'complete', 'detached': True, 'pid': pid})
        parent = {'schemaVersion': 1, 'kind': 'observer-parent-exit', 'runId': run,
                  'status': 'PASS', 'debuggerReaped': True, 'debuggerExitCode': 0,
                  'shutdownTimedOut': False, 'forcedTermination': False, 'cleanupErrors': [],
                  'resumeEligible': False, 'planSha256': 'b' * 64,
                  'controllerStatus': 'PASS', 'controllerDetached': True,
                  'controllerResultSha256': hashlib.sha256(result).hexdigest()}
        members[session + '/trace.jsonl'] = b''.join(encoded(row) for row in rows)
        members[session + '/result.json'] = result
        members[session + '/observer-parent.json'] = encoded(parent)
    members['evidence.jsonl'] = b''.join(encoded(row) for row in evidence)
    return members


def edit(members, name, **changes):
    row = json.loads(members[name]); row.update(changes); members[name] = encoded(row)


class MatrixIntegrityTests(unittest.TestCase):
    def analyze(self, members):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'matrix.zip'
            with zipfile.ZipFile(path, 'w') as z:
                for name, data in members.items():
                    z.writestr(name, data)
            before = path.read_bytes()
            out = m.analyze(path)
            self.assertEqual(path.read_bytes(), before)
            return out

    def assert_blocked(self, members):
        out = self.analyze(members)
        self.assertEqual(out['runtimeStatus'], 'BLOCKED')
        self.assertEqual(out['gates']['SYNC-001'], 'NOT RUN')
        self.assertFalse(any(v in ('OBSERVED', 'PARTIAL', 'PASS', 'GAP') for v in out['gates'].values()))
        return out

    def test_nonzero_debugger_exit_overrides_summary_pass(self):
        for code in (7, -11):
            with self.subTest(code=code):
                members = fixture()
                edit(members, 'pre-restart/observer-parent.json', debuggerExitCode=code)
                self.assert_blocked(members)

    def test_missing_parent_is_not_current_integrity_pass(self):
        members = fixture(); del members['pre-restart/observer-parent.json']
        out = self.assert_blocked(members)
        self.assertEqual(out['observations']['extendScriptProcessProjectChanges'], [1, 1])

    def test_empty_trace_cannot_prove_native_path(self):
        members = fixture(); members['pre-restart/trace.jsonl'] = b''
        self.assert_blocked(members)

    def test_positive_control_does_not_close_semantic_gates(self):
        out = self.analyze(fixture())
        self.assertEqual(out['schemaVersion'], 2)
        self.assertEqual(out['runtimeStatus'], 'PASS')
        self.assertEqual(out['reportedRuntimeStatus'], 'PASS')
        self.assertEqual(out['gates']['extendScriptOrigin'], 'OBSERVED')
        self.assertEqual(out['gates']['commonNativePath'], 'OBSERVED')
        self.assertEqual(out['gates']['restartProcess'], 'OBSERVED')
        for key in ('postCommitSemantics', 'restartReopen', 'otherPluginOrigin', 'activeCompSwitch'):
            self.assertEqual(out['gates'][key], 'UNPROVEN')

    def test_legacy_archive_keeps_observations_without_acceptance(self):
        members = fixture()
        for session in ('pre-restart', 'post-restart'):
            del members[session + '/observer-parent.json']
        edit(members, 'summary.json', collectorBuild={'sourceCommit': 'legacy'})
        out = self.assert_blocked(members)
        self.assertEqual(out['reportedRuntimeStatus'], 'PASS')
        self.assertEqual(out['sessions']['pre-restart']['hits'], 3)

    def test_abnormal_parent_flags_never_pass(self):
        changes = ({'debuggerExitCode': False}, {'debuggerExitCode': None},
                   {'debuggerReaped': False}, {'shutdownTimedOut': True},
                   {'forcedTermination': True}, {'cleanupErrors': ['OSError']},
                   {'status': 'BLOCKED'}, {'controllerDetached': False},
                   {'resumeEligible': True}, {'sessionError': 'ValueError'},
                   {'resultError': 'ValueError'}, {'abortError': 'OSError'})
        for change in changes:
            with self.subTest(change=change):
                members = fixture(); edit(members, 'pre-restart/observer-parent.json', **change)
                self.assert_blocked(members)

    def test_hash_binding_prevents_replaced_controller_result(self):
        members = fixture()
        edit(members, 'pre-restart/result.json', note='changed after parent decision')
        out = self.assert_blocked(members)
        self.assertIn('PARENT_RESULT_BINDING_MISMATCH', out['sessions']['pre-restart']['observerIntegrity']['reasons'])

    def test_controller_failure_or_wrong_pid_even_with_matching_hash(self):
        for changes in ({'status': 'FAIL'}, {'stage': 'aborted'}, {'detached': False}, {'pid': True}, {'pid': 99}):
            with self.subTest(changes=changes):
                members = fixture(); edit(members, 'pre-restart/result.json', **changes)
                edit(members, 'pre-restart/observer-parent.json',
                     controllerResultSha256=hashlib.sha256(members['pre-restart/result.json']).hexdigest())
                self.assert_blocked(members)

    def test_trace_corruption_and_limits_cannot_promote_claims(self):
        for issue in ('first', 'last', 'sequence', 'run', 'pid', 'count', 'limit', 'error', 'time', 'negative', 'overclaim', 'finish'):
            with self.subTest(issue=issue):
                members = fixture(); rows = m.rows_from_bytes(members['pre-restart/trace.jsonl'])
                if issue == 'first': rows.pop(0)
                elif issue == 'last': rows.pop()
                elif issue == 'sequence': rows[2]['sequence'] += 1
                elif issue == 'run': rows[2]['testRunId'] = 'another'
                elif issue == 'pid': rows[3]['pid'] = 123
                elif issue == 'count': rows[-1]['hits'] += 1
                elif issue == 'limit': rows[3]['kind'] = 'capture-limit'
                elif issue == 'error': rows[3]['kind'] = 'capture-error'
                elif issue == 'time': rows[3]['monotonicNs'] = 1
                elif issue == 'negative': rows[0]['monotonicNs'] = -1
                elif issue == 'overclaim': rows[3]['isNotificationProven'] = True
                elif issue == 'finish': rows[-2]['label'] = 'capture-aborted'
                members['pre-restart/trace.jsonl'] = b''.join(encoded(r) for r in rows)
                self.assert_blocked(members)

    def test_duplicate_and_incomplete_phase_windows(self):
        for issue in ('duplicate', 'unmatched', 'open'):
            with self.subTest(issue=issue):
                members = fixture(); rows = m.rows_from_bytes(members['pre-restart/trace.jsonl'])
                if issue == 'duplicate':
                    rows[5]['label'] = 'native-timing-start'; rows[7]['label'] = 'native-timing-done'
                elif issue == 'unmatched': rows[4]['label'] = 'wrong-done'
                else: rows[4]['label'] = 'other-marker'
                members['pre-restart/trace.jsonl'] = b''.join(encoded(r) for r in rows)
                self.assert_blocked(members)

    def test_zero_hit_valid_capture_is_not_native_path_evidence(self):
        members = fixture()
        rows = m.rows_from_bytes(members['pre-restart/trace.jsonl'])
        rows = [r for r in rows if r['kind'] != 'candidate-hit']
        rows[-1]['hits'] = 0
        for i, row in enumerate(rows, 1): row['sequence'] = i
        members['pre-restart/trace.jsonl'] = b''.join(encoded(r) for r in rows)
        out = self.analyze(members)
        self.assertEqual(out['runtimeStatus'], 'PASS')
        self.assertEqual(out['gates']['commonNativePath'], 'UNPROVEN')
        self.assertEqual(out['gates']['extendScriptOrigin'], 'UNPROVEN')

    def test_failed_or_unproven_script_not_credited_for_window_hit(self):
        for issue in ('failed', 'timeout', 'missing', 'duplicate', 'wrong-session'):
            with self.subTest(issue=issue):
                members = fixture(); rows = m.rows_from_bytes(members['evidence.jsonl'])
                if issue == 'failed': rows[1]['result']['ok'] = False
                elif issue == 'timeout': rows[1]['result']['timedOut'] = True
                elif issue == 'missing': rows.pop(1)
                elif issue == 'duplicate': rows.append(copy.deepcopy(rows[1]))
                else: rows[1]['session'] = 'unrelated'
                members['evidence.jsonl'] = b''.join(encoded(r) for r in rows)
                out = self.analyze(members)
                self.assertEqual(out['gates']['extendScriptOrigin'], 'UNPROVEN')
                self.assertEqual(out['observations']['extendScriptProcessProjectChanges'], [1, 1])

    def test_summary_fail_not_promoted_by_good_session_records(self):
        members = fixture(); edit(members, 'summary.json', status='BLOCKED')
        self.assert_blocked(members)

    def test_valid_snapshot_is_not_a_postcommit_proof(self):
        members = fixture()
        members['evidence.jsonl'] += encoded({'kind': 'snapshot-after', 'session': 'unrelated',
                                              'snapshot': {'ok': True, 'value': 'comp=realistic', 'timedOut': False}})
        out = self.analyze(members)
        self.assertTrue(out['observations']['snapshotOracleValid'])
        self.assertEqual(out['gates']['postCommitSemantics'], 'UNPROVEN')
        self.assertEqual(out['gates']['activeCompSwitch'], 'UNPROVEN')

    def test_pid_change_must_match_sessions_and_never_proves_reopen(self):
        members = fixture(); rows = m.rows_from_bytes(members['evidence.jsonl'])
        rows[0]['oldPid'] = 999
        members['evidence.jsonl'] = b''.join(encoded(r) for r in rows)
        out = self.analyze(members)
        self.assertEqual(out['gates']['restartProcess'], 'UNPROVEN')
        self.assertEqual(out['gates']['restartReopen'], 'UNPROVEN')

    def test_resumed_layout_keeps_capture_windows_separate(self):
        members = fixture()
        old = m.rows_from_bytes(members.pop('pre-restart/trace.jsonl'))
        result = members.pop('pre-restart/result.json')
        parent = json.loads(members.pop('pre-restart/observer-parent.json'))
        for name, selected, partial in (('pre-restart-partial', ('native-timing', 'native-comp-switch'), True),
                                        ('pre-restart-resume', ('extendscript-origin',), False)):
            rows = [copy.deepcopy(old[0]), copy.deepcopy(old[1])]
            for i in range(2, len(old) - 2, 3):
                if old[i]['label'][:-6] in selected:
                    rows.extend(copy.deepcopy(old[i:i+3]))
            rows += copy.deepcopy(old[-2:])
            rows[-2]['label'] = 'capture-aborted' if partial else 'capture-finished'
            rows[-1]['hits'] = len(selected)
            run = 'runtime_' + name.replace('-', '_')
            for i, row in enumerate(rows, 1): row.update(sequence=i, testRunId=run)
            state = json.loads(result)
            if partial: state.update(status='BLOCKED', stage='aborted')
            raw = encoded(state)
            pr = dict(parent, runId=run, status=state['status'], controllerStatus=state['status'],
                      resumeEligible=partial, controllerResultSha256=hashlib.sha256(raw).hexdigest())
            if partial: pr['sessionError'] = 'KeyboardInterrupt'
            members[name + '/trace.jsonl'] = b''.join(encoded(r) for r in rows)
            members[name + '/result.json'] = raw
            members[name + '/observer-parent.json'] = encoded(pr)
        edit(members, 'summary.json', sessions=['pre-restart-partial', 'pre-restart-resume', 'post-restart'])
        erows = m.rows_from_bytes(members['evidence.jsonl']); erows[1]['session'] = 'pre-restart-resume'
        members['evidence.jsonl'] = b''.join(encoded(r) for r in erows)
        out = self.analyze(members)
        self.assertEqual(out['runtimeStatus'], 'PASS')
        self.assertEqual(out['gates']['extendScriptOrigin'], 'OBSERVED')
        self.assertEqual(len(out['sessions']), 3)
        edit(members, 'pre-restart-partial/observer-parent.json', resumeEligible=False)
        self.assert_blocked(members)

    def test_reused_run_id_blocks_even_with_self_consistent_trace(self):
        members = fixture()
        run = json.loads(members['pre-restart/observer-parent.json'])['runId']
        edit(members, 'post-restart/observer-parent.json', runId=run)
        rows = m.rows_from_bytes(members['post-restart/trace.jsonl'])
        for row in rows: row['testRunId'] = run
        members['post-restart/trace.jsonl'] = b''.join(encoded(r) for r in rows)
        self.assert_blocked(members)

    def test_bad_json_and_non_utf8_are_not_silently_repaired(self):
        for data in (b'\xff', b'[]', b'{"status":"PASS","status":"FAIL"}'):
            with self.subTest(data=data), self.assertRaises(ValueError):
                members = fixture(); members['summary.json'] = data; self.analyze(members)
        with self.assertRaises(ValueError): m.rows_from_bytes(b'{"kind":"capture-end"}')

    def test_zip_duplicate_traversal_and_symlink_refused(self):
        import warnings
        with tempfile.TemporaryDirectory() as td:
            for issue in ('duplicate', 'traversal', 'symlink'):
                path = Path(td) / (issue + '.zip')
                with zipfile.ZipFile(path, 'w') as z, warnings.catch_warnings():
                    warnings.simplefilter('ignore', UserWarning)
                    for name, data in fixture().items(): z.writestr(name, data)
                    if issue == 'duplicate': z.writestr('summary.json', b'{}')
                    elif issue == 'traversal': z.writestr('../other', b'untouched')
                    else:
                        entry = zipfile.ZipInfo('link'); entry.create_system = 3
                        entry.external_attr = 0o120777 << 16; z.writestr(entry, b'/outside')
                with self.subTest(issue=issue), self.assertRaises(ValueError): m.analyze(path)

    def test_zip_limits_before_member_read(self):
        for name, limit in (('MAX_MEMBER_BYTES', 10), ('MAX_TOTAL_BYTES', 10), ('MAX_MEMBERS', 2)):
            with self.subTest(name=name), mock.patch.object(m, name, limit), self.assertRaises(ValueError):
                self.analyze(fixture())

    def test_unknown_session_layout_refused(self):
        for layout in (['pre-restart', 'pre-restart', 'post-restart'], ['../outside'], 'pre-restart'):
            with self.subTest(layout=layout), self.assertRaises(ValueError):
                members = fixture(); edit(members, 'summary.json', sessions=layout); self.analyze(members)

    def test_cli_blocked_analysis_has_nonzero_status_and_preserves_input(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'matrix.zip'; output = Path(td) / 'analysis.json'
            members = fixture(); del members['pre-restart/observer-parent.json']
            with zipfile.ZipFile(path, 'w') as z:
                for name, data in members.items(): z.writestr(name, data)
            self.assertEqual(m.main([str(path), '--output', str(output)]), 2)
            self.assertEqual(json.loads(output.read_text())['runtimeStatus'], 'BLOCKED')

    def test_jsonl_and_window_counts_are_bounded(self):
        with mock.patch.object(m, 'MAX_JSONL_ROWS', 1), self.assertRaises(ValueError):
            m.rows_from_bytes(encoded({'kind': 'x'}) * 2)
        rows = [{'kind': 'phase', 'label': 'x-start', 'monotonicNs': 1},
                {'kind': 'phase', 'label': 'x-done', 'monotonicNs': 2}]
        with mock.patch.object(m, 'MAX_WINDOWS', 0), self.assertRaises(ValueError):
            m.phase_windows(rows)

    def test_blocked_phase_is_not_promoted_by_conflicting_success_record(self):
        members = fixture()
        members['evidence.jsonl'] += encoded({'kind': 'step-blocked', 'session': 'pre-restart',
                                               'phase': 'extendscript-origin', 'reason': 'unresolved'})
        self.assertEqual(self.analyze(members)['gates']['extendScriptOrigin'], 'UNPROVEN')

    def test_parent_record_with_invalid_run_id_is_diagnostic_not_pass(self):
        members = fixture(); edit(members, 'pre-restart/observer-parent.json', runId={'bad': 'type'})
        self.assert_blocked(members)

if __name__ == '__main__':
    unittest.main()
