"""macOS exact-kit selection diagnostics and AppleScript compile check; no AE."""
import ast
import json
from pathlib import Path
import plistlib
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def main():
    commit = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    archive = ROOT / 'dist/notification-collector' / commit / 'FSTR-AE-Collector.zip'
    with tempfile.TemporaryDirectory(prefix='fstr-selection-') as temporary:
        temp = Path(temporary)
        with zipfile.ZipFile(archive) as z:
            z.extractall(temp / 'kit')  # own exact allowlisted build; not external input
        kit = temp / 'kit/FSTR-AE-Collector'
        tree = ast.parse((kit / 'collect_app.py').read_text())
        text = next(ast.literal_eval(node.value) for node in tree.body
                    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'CHOOSE_APP_SCRIPT' for t in node.targets))
        script = temp / 'choose.applescript'
        script.write_text(text)
        subprocess.run(['/usr/bin/osacompile', '-o', str(temp / 'choose.scpt'), str(script)], check=True, timeout=30)
        # Valid-looking application name but incompatible metadata must be recorded,
        # never scanned or mistaken for a missing installation.
        app = temp / 'Тест ; $(echo no)/Adobe After Effects 2025.app'
        (app / 'Contents').mkdir(parents=True)
        metadata = dict(CFBundleIdentifier='com.adobe.AfterEffects', CFBundleShortVersionString='26.0',
                        CFBundleVersion='SYNTHETIC-SELECTION-NOT-ADOBE', CFBundleExecutable='NeverLaunched')
        (app / 'Contents/Info.plist').write_bytes(plistlib.dumps(metadata))
        done = subprocess.run(['bash', str(kit / 'Collect-AE.command'), '--app', str(app),
                               '--output', str(temp / 'reports')], capture_output=True, text=True, timeout=30)
        if done.returncode != 2:
            raise RuntimeError('Wrong metadata was not blocked: ' + done.stdout + done.stderr)
        reports = list((temp / 'reports').glob('*.zip'))
        if len(reports) != 1:
            raise RuntimeError('Expected one failure report')
        with zipfile.ZipFile(reports[0]) as z:
            report = json.loads(z.read('report.json'))
        if report['collectionStatus'] != 'BLOCKED' or report['selection']['candidate']['metadata'] != metadata:
            raise RuntimeError('Selected application rejection metadata was lost')
        if report.get('modules') or report['collectorBuild']['sourceCommit'] != commit:
            raise RuntimeError('Wrong scope or build identity')
        evidence = dict(status='PASS', sourceCommit=commit, chooserSyntax='PASS',
                        selectedAppRejectionFromExactKit='PASS', interactiveChooserUI='NOT RUN',
                        actualAE='NOT RUN', scope='AppleScript compilation and literal explicit-path diagnostics, not an Adobe run')
        output = ROOT / 'dist/notification-evidence/selection-smoke.json'
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(evidence, indent=2) + '\n')
        print(json.dumps(evidence))


if __name__ == '__main__':
    main()
