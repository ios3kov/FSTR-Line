#!/usr/bin/env python3
"""Package a clean, identified diagnostic kit without installing it."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'research/ae-notifications'
NAMES = ('Collect-AE.command', 'collect_app.py', 'inspect_binary.py', 'README.txt')


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True).strip()


def main():
    if git('status', '--porcelain'):
        raise SystemExit('Dirty source: diagnostic handoff refused')
    commit = git('rev-parse', 'HEAD')
    output = ROOT / 'dist/notification-collector' / commit
    output.mkdir(parents=True, exist_ok=False)
    kit = output / 'FSTR-AE-Collector'
    kit.mkdir()
    manifest = dict(schemaVersion=1, sourceCommit=commit, sourceState='clean',
                    buildId='fstr-static-collector-' + commit[:12], files={})
    for name in NAMES:
        source = SOURCE / name
        if source.is_symlink():
            raise SystemExit('Unexpected symlink source')
        shutil.copyfile(source, kit / name)
        (kit / name).chmod(0o755 if name.endswith('.command') else 0o644)
        manifest['files'][name] = hashlib.sha256(source.read_bytes()).hexdigest()
    (kit / 'build-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    archive = output / 'FSTR-AE-Collector.zip'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as package:
        for name in (*NAMES, 'build-manifest.json'):
            package.write(kit / name, 'FSTR-AE-Collector/' + name)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / 'SHA256.txt').write_text(digest + '  ' + archive.name + '\n', encoding='utf-8')
    if git('status', '--porcelain'):
        raise SystemExit('Build changed source tree')
    print(json.dumps({'archive': str(archive), 'sha256': digest, 'sourceCommit': commit}))


if __name__ == '__main__':
    main()
