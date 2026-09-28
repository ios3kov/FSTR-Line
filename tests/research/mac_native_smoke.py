"""Mac-only exact-package static collection and real debugger positive control."""
import hashlib
import json
from pathlib import Path
import plistlib
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def main():
    if sys.platform != 'darwin':
        raise SystemExit('BLOCKED: requires macOS, never treat as PASS')
    commit = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    output = ROOT / 'dist/notification-evidence'
    output.mkdir(parents=True, exist_ok=True)
    packaged = ROOT / 'dist/notification-collector' / commit / 'FSTR-AE-Collector.zip'
    observed = json.loads((ROOT / 'tests/research/fixtures/ae-25.6-observed-metadata.json').read_text())
    with tempfile.TemporaryDirectory(prefix='fstr-owned-native-') as temporary:
        directory = Path(temporary)
        with zipfile.ZipFile(packaged) as archive:
            archive.extractall(directory / 'unpacked')  # our allowlisted builder output
        kit = directory / 'unpacked/FSTR-AE-Collector'
        app = directory / observed['appName']
        # Actual metadata is from a report, but BOTH executable copies are OUR
        # compiled control. This does not make the fixture an Adobe installation.
        binary = directory / 'fstr-owned-fixture'
        app_binary = app / 'Contents/MacOS' / observed['metadata']['CFBundleExecutable']
        app_binary.parent.mkdir(parents=True)
        subprocess.run(['xcrun', 'clang++', '-g', '-O0', '-std=c++17',
                        str(ROOT / 'tests/research/native_control.cpp'), '-o', str(binary)], check=True, timeout=60)
        shutil.copyfile(binary, app_binary)
        (app / 'Contents/Info.plist').write_bytes(plistlib.dumps(observed['metadata']))
        before = hashlib.sha256(binary.read_bytes()).hexdigest()
        completed = subprocess.run(['bash', str(kit / 'Collect-AE.command'), '--app', str(app),
                                    '--output', str(directory / 'reports')], capture_output=True,
                                   text=True, timeout=90)
        if completed.returncode:
            raise RuntimeError('Exact packaged collector failed: ' + completed.stdout + completed.stderr)
        archives = list((directory / 'reports').glob('*.zip'))
        assert len(archives) == 1
        with zipfile.ZipFile(archives[0]) as archive:
            assert archive.namelist() == ['report.json']
            report = json.loads(archive.read('report.json'))
        assert report['collectionStatus'] == 'PASS' and report['SYNC-001'] == 'NOT RUN'
        assert report['collectorBuild']['sourceCommit'] == commit
        assert report['selection']['candidate']['metadata'] == observed['metadata']
        assert report['modules'][0]['relativePath'] == 'Contents/MacOS/After Effects'
        assert report['application']['runtimeIdentityVerified'] is False
        assert report['application']['exactBuild101Verified'] is False
        inspected = report['modules'][0]['inspection']
        assert inspected['sha256'] == before == hashlib.sha256(app_binary.read_bytes()).hexdigest()
        ids = {s['uuid'].lower() for s in inspected['slices'] if s['uuid']}
        actual_uuid_output = subprocess.check_output(['xcrun', 'dwarfdump', '--uuid', str(binary)], text=True)
        actual_ids = {s.lower() for s in re.findall(r'UUID: ([A-Fa-f0-9-]{36})', actual_uuid_output)}
        assert ids == actual_ids and ids
        assert any('fstr_fixture_notification' in symbol['name']
                   for s in inspected['slices'] for symbol in s['matchingSymbols'])
        result_path = directory / 'lldb-result.json'
        control = ROOT / 'tests/research/real_lldb_control.py'
        call = 'script real_lldb_control.run(lldb.debugger, {}, {}, {})'.format(
            json.dumps(str(binary)), json.dumps(str(result_path)), json.dumps(str(ROOT)))
        completed = subprocess.run(['xcrun', 'lldb', '--batch', '--no-lldbinit',
            '-o', 'script import sys; sys.dont_write_bytecode = True',
            '-o', 'command script import ' + shlex.quote(str(ROOT / 'research/ae-notifications/trace_callback.py')),
            '-o', 'command script import ' + shlex.quote(str(control)), '-o', call],
            capture_output=True, text=True, timeout=90)
        if completed.returncode or not result_path.is_file():
            raise RuntimeError('LLDB control did not PASS: ' + completed.stdout + completed.stderr)
        control_result = json.loads(result_path.read_text())
        assert control_result['status'] == 'PASS', json.dumps(control_result)
        assert control_result['fixtureSha256'] == before
        assert control_result['moduleUUID'].lower() in ids
        evidence = dict(status='PASS', sourceCommit=commit,
            kitSha256=hashlib.sha256(packaged.read_bytes()).hexdigest(),
            scope='Exact collector ZIP on compiled Mach-O fixture with observed AE metadata, and real LLDB. NOT an AE test.',
            observedMetadataReportSha256=observed['reportSha256'],
            observedMetadataAcceptance='PASS',
            staticCollection='PASS', uuidComparedWithDwarfdump='PASS',
            control=control_result, actualAE='NOT RUN', **{'SYNC-001': 'NOT RUN'})
        (output / 'mac-native-smoke.json').write_text(json.dumps(evidence, indent=2) + '\n')
        print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
