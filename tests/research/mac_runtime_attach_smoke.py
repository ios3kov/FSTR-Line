"""Mac-only parent/LLDB IPC smoke. Every run owns its process and retains evidence."""
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

from smoke_evidence import BoundedLog, reap_owned, save_evidence
from fixture_liveness import SOURCE, require_progress

ROOT = Path(__file__).resolve().parents[2]


def _symbol_file_address(binary, name):
    text = subprocess.check_output(['xcrun', 'nm', '-nm', str(binary)], text=True, timeout=30)
    for line in text.splitlines():
        if line.rstrip().endswith(' ' + name):
            match = re.match(r'^([0-9A-Fa-f]+)\s', line)
            if match:
                return int(match.group(1), 16)
    raise RuntimeError('Fixture symbol address unavailable')


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_once(commit, archive):
    evidence = {'status': 'FAIL', 'sourceCommit': commit,
                'kitSha256': hashlib.sha256(archive.read_bytes()).hexdigest()}
    with tempfile.TemporaryDirectory(prefix='fstr-runtime-smoke-') as td:
        t = Path(td).resolve()
        target_process = lldb_process = log = None
        try:
            with zipfile.ZipFile(archive) as z:
                for entry in z.infolist():
                    dest = (t / 'kit' / entry.filename).resolve()
                    if not dest.is_relative_to(t / 'kit') or (entry.external_attr >> 16) & 0o170000 == 0o120000:
                        raise RuntimeError('Unsafe kit entry')
                z.extractall(t / 'kit')
            kit = t / 'kit/FSTR-AE-Runtime'
            manifest = json.loads((kit / 'build-manifest.json').read_text())
            if manifest['sourceCommit'] != commit or manifest['sourceState'] != 'clean':
                raise RuntimeError('Kit source identity mismatch')
            for name, digest in manifest['files'].items():
                path = (kit / name).resolve()
                if not path.is_relative_to(kit) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    raise RuntimeError('Kit payload mismatch')
            evidence['buildId'] = manifest['buildId']
            protocol = _load(kit / 'runtime_protocol.py', 'fixture_runtime_protocol')
            src = t / 'fixture.cpp'
            src.write_text(SOURCE)
            binary = t / 'fstr-runtime-fixture'
            subprocess.run(['xcrun', 'clang++', '-g', '-O0', str(src), '-o', str(binary)], check=True, timeout=60)
            uuid_text = subprocess.check_output(['xcrun', 'dwarfdump', '--uuid', str(binary)], text=True, timeout=30)
            match = re.search(r'UUID: ([A-Fa-f0-9-]{36})', uuid_text)
            if not match:
                raise RuntimeError('Fixture UUID unavailable')
            digest = hashlib.sha256(binary.read_bytes()).hexdigest()
            address = _symbol_file_address(binary, '_fstr_runtime_candidate')
            counter = t / 'fixture-counter'
            target_process = subprocess.Popen([str(binary), str(counter)])
            evidence['fixtureBeforeAttach'] = require_progress(target_process, counter)
            control = t / 'control.jsonl'
            ack = t / 'ack.jsonl'
            control.touch()
            ack.touch()
            plan = {'runId': 'fixture', 'pid': target_process.pid, 'executable': str(binary),
                    'modules': [{'key': 'fixture', 'path': str(binary), 'sha256': digest, 'uuid': match[1]}],
                    'breakpoints': [{'label': 'fixture-event', 'role': 'boundary-candidate', 'module': 'fixture',
                                     'fileAddress': hex(address), 'minLocations': 1, 'maxLocations': 1}],
                    'durationSeconds': 10, 'maxEvents': 500, 'maxFrames': 4, 'diagnosticStages': True,
                    'controlPath': str(control), 'ackPath': str(ack),
                    'tracePath': str(t / 'trace.jsonl'), 'resultPath': str(t / 'result.json')}
            (t / 'plan.json').write_text(json.dumps(plan))
            args = ['xcrun', 'lldb', '--batch', '--no-lldbinit']
            for name in ('trace_callback', 'runtime_protocol', 'runtime_control'):
                args.extend(['-o', 'command script import ' + json.dumps(str(kit / (name + '.py')))])
            args.extend(['-o', 'script runtime_control.run(lldb.debugger, ' + json.dumps(str(t / 'plan.json')) + ')'])
            lldb_process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                           stderr=subprocess.STDOUT)
            log = BoundedLog(lldb_process.stdout, t / 'lldb.log')
            protocol.wait_for_record(ack, kind='ready', sequence=0, process=lldb_process, timeout=10)
            protocol.send_phase(control, ack, 1, 'fixture-start', lldb_process, 5)
            time.sleep(.5)
            protocol.send_phase(control, ack, 2, 'fixture-done', lldb_process, 5)
            protocol.send_finish(control, 3)
            evidence['parentStage'] = 'wait-for-lldb-exit'
            if lldb_process.wait(timeout=15) != 0:
                raise RuntimeError('LLDB exited unsuccessfully')
            result = json.loads((t / 'result.json').read_text())
            if result['status'] != 'PASS' or not result.get('detached'):
                raise RuntimeError('Controller did not confirm clean detach')
            records = protocol.read_complete_jsonl(ack)
            stages = [r['stage'] for r in records if r.get('kind') == 'controller-stage']
            if not stages or stages[-1] != 'controller-return' or any(r.get('diagnosticErrorCount') for r in records):
                raise RuntimeError('Controller return marker missing')
            rows = [json.loads(x) for x in (t / 'trace.jsonl').read_text().splitlines()]
            hits = [r for r in rows if r['kind'] == 'candidate-hit']
            phases = [r.get('label') for r in rows if r['kind'] == 'phase']
            if not hits or not {'fixture-start', 'fixture-done'} <= set(phases):
                raise RuntimeError('Missing hits or phase IPC')
            if any(r['isNotificationProven'] or r['commitPhase'] != 'UNKNOWN' for r in hits):
                raise RuntimeError('Observer overclaimed semantics')
            evidence['parentStage'] = 'fixture-post-detach-progress'
            evidence['fixtureAfterDetach'] = require_progress(target_process, counter)
            evidence.update(status='PASS', parentStage='verified', hits=len(hits), detached=True, phaseIPC='PASS')
        except Exception as error:
            # Do not print TimeoutExpired.args (contains test filesystem paths).
            evidence.update(status='FAIL', errorType=type(error).__name__)
        finally:
            if evidence['status'] == 'PASS' and target_process.poll() is not None:
                evidence.update(status='FAIL', errorType='FixtureExitedBeforeCleanup')
            evidence['debuggerCleanup'] = reap_owned(lldb_process)
            evidence['fixtureCleanup'] = reap_owned(target_process, resume=True)
            if log:
                evidence['logCapture'] = log.finish()
            if not all(evidence[k]['reaped'] for k in ('debuggerCleanup', 'fixtureCleanup')) or \
                    (log and not evidence['logCapture']['complete']):
                evidence['status'] = 'FAIL'
            path = save_evidence(t, ROOT / 'dist/notification-evidence/runtime-attach', evidence)
            summary = json.loads(path.read_text())
            text = summary['files'].get('ack.jsonl', {}).get('text', '')
            records = [json.loads(line) for line in text.splitlines() if line.startswith('{') and line.endswith('}')]
            stages = [r['stage'] for r in records if r.get('kind') == 'controller-stage']
            print(json.dumps({k: v for k, v in evidence.items() if k != 'files'} | {
                'lastControllerStage': stages[-1] if stages else None,
                'evidence': str(path.relative_to(ROOT)), 'SYNC-001': 'NOT RUN'}), flush=True)
        return evidence['status'] == 'PASS'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=int, default=1)
    args = parser.parse_args(argv)
    if not 1 <= args.runs <= 5:
        parser.error('--runs must be between 1 and 5')
    if sys.platform != 'darwin':
        raise SystemExit('BLOCKED: macOS required')
    commit = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    archive = ROOT / 'dist/runtime-research' / commit / 'FSTR-AE-Runtime.zip'
    for _ in range(args.runs):
        if not run_once(commit, archive):
            return 1  # Stop at first FAIL; never retry to green.
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
