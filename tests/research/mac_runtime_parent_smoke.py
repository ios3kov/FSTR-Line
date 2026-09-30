"""Exact packaged runtime_probe parent + real LLDB, only an owned Mach-O target."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from unittest import mock

from mac_runtime_attach_smoke import _load, _symbol_file_address
from smoke_evidence import reap_owned, save_evidence

ROOT = Path(__file__).resolve().parents[2]


def run_once(commit, archive):
    evidence = {'status': 'FAIL', 'sourceCommit': commit, 'fixtureType': 'actual-runtime-parent',
                'kitSha256': hashlib.sha256(archive.read_bytes()).hexdigest()}
    with tempfile.TemporaryDirectory(prefix='fstr-parent-smoke-') as td:
        work = Path(td).resolve()
        target = None
        session = work / 'capture'
        try:
            # Exercise quoted LLDB imports as well as the actual packaged entry point.
            extraction = work / 'kit with spaces'
            with zipfile.ZipFile(archive) as z:
                for entry in z.infolist():
                    dest = (extraction / entry.filename).resolve()
                    if not dest.is_relative_to(extraction) or (entry.external_attr >> 16) & 0o170000 == 0o120000:
                        raise RuntimeError('Unsafe kit entry')
                z.extractall(extraction)
            kit = extraction / 'FSTR-AE-Runtime'
            manifest = json.loads((kit / 'build-manifest.json').read_text())
            if manifest['sourceCommit'] != commit or manifest['sourceState'] != 'clean':
                raise RuntimeError('Kit source identity mismatch')
            for name, digest in manifest['files'].items():
                path = (kit / name).resolve()
                if not path.is_relative_to(kit) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    raise RuntimeError('Kit payload mismatch')
            evidence['buildId'] = manifest['buildId']
            probe = _load(kit / 'runtime_probe.py', 'actual_runtime_parent_fixture')
            source = work / 'owned.cpp'
            source.write_text('#include <unistd.h>\nextern "C" __attribute__((noinline)) void fstr_runtime_candidate(){}\nint main(){for(int i=0;i<3000;i++){fstr_runtime_candidate(); usleep(20000);} return 0;}\n')
            binary = work / 'fstr-parent-fixture'
            subprocess.run(['xcrun', 'clang++', '-g', '-O0', str(source), '-o', str(binary)], check=True, timeout=60)
            uid_text = subprocess.check_output(['xcrun', 'dwarfdump', '--uuid', str(binary)], text=True, timeout=30)
            match = re.search(r'UUID: ([A-Fa-f0-9-]{36})', uid_text)
            if not match:
                raise RuntimeError('Fixture UUID unavailable')
            modules = [{'key':'fixture', 'path':str(binary), 'uuid':match[1],
                        'sha256':hashlib.sha256(binary.read_bytes()).hexdigest()}]
            bp = {'label':'fixture-event', 'role':'boundary-candidate', 'module':'fixture',
                  'fileAddress':hex(_symbol_file_address(binary, '_fstr_runtime_candidate')),
                  'minLocations':1, 'maxLocations':1}
            candidates = {'breakpoints':[bp], 'durationSeconds':10,
                          'aeBundleId':'org.fstr.owned-fixture', 'maxFrames':4,
                          'attachReadyTimeoutSeconds':10, 'ackTimeoutSeconds':5,
                          'shutdownTimeoutSeconds':15}
            target = subprocess.Popen([str(binary)])
            # Only the unrelated snapshot/UI operations are replaced. Launch, IPC,
            # controller, result acceptance and debugger shutdown are actual source.
            with mock.patch.object(probe, 'snapshot', return_value={'ok':True, 'value':'owned'}), \
                 mock.patch('builtins.input', side_effect=lambda *_: time.sleep(.3)):
                result = probe.run_observer_session(binary, target.pid, modules, candidates,
                    [{'label':'owned', 'instructionRu':'Owned-process parent smoke, not AE.'}],
                    work, 'capture', work / 'evidence.jsonl')
            ledger = json.loads((session / 'observer-parent.json').read_text())
            evidence['parentAcceptance'] = ledger
            if ledger['status'] != 'PASS' or not probe._clean_debugger_exit(ledger):
                raise RuntimeError('Parent did not confirm clean debugger exit')
            if result.get('pid') != target.pid or result.get('detached') is not True or target.poll() is not None:
                raise RuntimeError('Detached fixture did not survive parent return')
            rows = probe.runtime_protocol.read_complete_jsonl(session / 'trace.jsonl')
            hits = [row for row in rows if row.get('kind') == 'candidate-hit']
            phases = {row.get('label') for row in rows if row.get('kind') == 'phase'}
            if not hits or not {'owned-start', 'owned-done'} <= phases:
                raise RuntimeError('Missing real breakpoint hits or phase IPC')
            if any(row['isNotificationProven'] or row['commitPhase'] != 'UNKNOWN' for row in hits):
                raise RuntimeError('Observer overclaimed notification semantics')
            evidence.update(status='PASS', hits=len(hits), fixtureAliveAfterDetach=True)
        except Exception as error:
            evidence.update(status='FAIL', errorType=type(error).__name__)
        finally:
            evidence['fixtureCleanup'] = reap_owned(target, resume=True)
            if not evidence['fixtureCleanup']['reaped']:
                evidence['status'] = 'FAIL'
            if (session / 'observer-parent.json').exists():
                evidence['parentAcceptance'] = json.loads((session / 'observer-parent.json').read_text())
            path = save_evidence(session, ROOT / 'dist/notification-evidence/runtime-attach', evidence)
            print(json.dumps({**evidence, 'evidence':str(path.relative_to(ROOT)), 'SYNC-001':'NOT RUN'}))
        return evidence['status'] == 'PASS'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=int, default=5)
    args = parser.parse_args(argv)
    if not 1 <= args.runs <= 5:
        parser.error('--runs must be between 1 and 5')
    if sys.platform != 'darwin':
        raise SystemExit('BLOCKED: macOS required')
    commit = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    archive = ROOT / 'dist/runtime-research' / commit / 'FSTR-AE-Runtime.zip'
    for _ in range(args.runs):
        if not run_once(commit, archive):
            return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
