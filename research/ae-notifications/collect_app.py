#!/usr/bin/env python3
"""Bounded read-only AE bundle collection. Does not start/attach/modify After Effects."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import stat
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile

MAGICS = {bytes.fromhex(x) for x in ('cffaedfe', 'cefaedfe', 'feedfacf', 'feedface',
                                    'cafebabe', 'bebafeca', 'cafebabf', 'bfbafeca')}
TOOLS = ('Collect-AE.command', 'collect_app.py', 'inspect_binary.py', 'README.txt')
MAX_FILE = 2 * 1024**3


class Blocked(Exception):
    pass


def require(value, message):
    if not value:
        raise ValueError(message)


def regular_read(path, root, limit):
    """No symlink/device reads; every input must remain in the selected bundle."""
    require(not path.is_symlink() and path.resolve().is_relative_to(root), 'Unsafe input path')
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode), 'Regular input file required')
        data = os.read(fd, limit)
        after = os.fstat(fd)
        require((before.st_ino, before.st_size, before.st_mtime_ns) ==
                (after.st_ino, after.st_size, after.st_mtime_ns), 'Input changed during read')
        return data, before
    finally:
        os.close(fd)


def identity(app):
    require(not app.is_symlink() and app.is_dir(), 'An actual application directory is required')
    app = app.resolve(strict=True)
    raw, info = regular_read(app / 'Contents/Info.plist', app, 1024 * 1024 + 1)
    require(info.st_size <= 1024 * 1024, 'Oversized Info.plist')
    values = plistlib.loads(raw)
    require(isinstance(values, dict), 'Invalid Info.plist')
    bundle = values.get('CFBundleIdentifier')
    version = values.get('CFBundleShortVersionString')
    executable = values.get('CFBundleExecutable')
    if bundle != 'com.adobe.AfterEffects' or not isinstance(version, str) or not re.match(r'^25\.6(?:\.|$)', version):
        raise Blocked('Expected an After Effects 25.6 application; no other version was scanned')
    require(isinstance(executable, str) and executable not in ('', '.', '..') and
            Path(executable).name == executable and '\\' not in executable, 'Invalid executable name')
    binary = app / 'Contents/MacOS' / executable
    magic, _ = regular_read(binary, app, 4)
    require(magic in MAGICS, 'Main executable is not Mach-O')
    return app, binary, {'bundleId': bundle, 'shortVersion': version,
        'bundleVersion': str(values.get('CFBundleVersion', 'unknown')),
        'plistSha256': hashlib.sha256(raw).hexdigest(),
        'runtimeIdentityVerified': False, 'exactBuild101Verified': False}


def discover(roots):
    """Only immediate .apps and one Adobe After Effects subdirectory; no whole-disk search."""
    found = []
    for root in roots:
        if not root.is_dir() or root.is_symlink():
            continue
        for item in sorted(root.iterdir())[:1000]:
            candidates = [item] if item.suffix == '.app' else []
            if item.is_dir() and not item.is_symlink() and item.name.startswith('Adobe After Effects'):
                candidates += sorted(item.glob('*.app'))[:20]
            for candidate in candidates:
                try:
                    app, _, _ = identity(candidate)
                    if app not in found:
                        found.append(app)
                except (OSError, ValueError, Blocked, plistlib.InvalidFileException):
                    pass
    if len(found) != 1:
        raise Blocked('No unique AE 25.6 installation found. Pass --app with the exact .app path')
    return found[0]


def scan_files(app, main, max_files):
    yield main
    count = 0
    for directory, dirs, files in os.walk(app / 'Contents', followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(directory) / d).is_symlink())
        for name in sorted(files):
            count += 1
            if count > max_files:
                raise Blocked('File enumeration limit reached')
            path = Path(directory) / name
            # Never inspect sample projects, credentials, caches or user data.
            if path == main or path.is_symlink() or path.suffix.lower() in ('.aep', '.aepx', '.prproj'):
                continue
            try:
                magic, _ = regular_read(path, app, 4)
            except (OSError, ValueError):
                raise Blocked('An application file could not be inspected') from None
            if magic in MAGICS:
                yield path


def redact(value):
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        value = re.sub(r'/(Users|home)/[^/\s"<>]+', r'/\1/[user]', value)
        value = re.sub(r'[A-Za-z]:\\Users\\[^\\\s"<>]+', r'[drive]:\\Users\\[user]', value)
        return re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[email]', value)
    return value


def inspect_module(binary, workspace, timeout):
    tool = Path(__file__).with_name('inspect_binary.py')
    result = subprocess.run([sys.executable, '-I', '-B', str(tool), str(binary),
        '--ae-build', '25.6 (metadata only)', '--output', str(workspace),
        '--max-scan-mib', '32', '--max-leads', '100'],
        timeout=timeout, capture_output=True, text=True)
    if result.returncode:
        raise ValueError('Inspector rejected this module')
    reports = list(workspace.glob('*/identity.json'))
    require(len(reports) == 1 and reports[0].stat().st_size < 2 * 1024**2, 'Invalid worker report')
    return redact(json.loads(reports[0].read_text(encoding='utf-8')))


def collect(app, inspector=inspect_module, max_files=20000, max_modules=256,
            max_bytes=8 * 1024**3, max_seconds=300):
    require(1 <= max_modules <= 1024 and 1 <= max_files <= 100000 and
            1 <= max_bytes <= 32 * 1024**3 and 1 <= max_seconds <= 1800, 'Invalid collection bounds')
    app, main, meta = identity(app)
    report = {'schemaVersion': 1, 'collectionStatus': 'PASS', 'application': meta,
        'scope': 'On-disk modules inside selected app only; not the loaded-process module set',
        'runtimeTrace': 'NOT RUN', 'SYNC-001': 'NOT RUN', 'notificationCandidate': None,
        'modules': [], 'limits': [], 'bytesInspected': 0,
        'environment': {'system': platform.system(), 'release': platform.release(),
                        'machine': platform.machine(), 'python': platform.python_version()}}
    started = time.monotonic()
    try:
        for binary in scan_files(app, main, max_files):
            remaining = max_seconds - (time.monotonic() - started)
            _, before = regular_read(binary, app, 4)
            if (remaining <= 0 or len(report['modules']) >= max_modules or before.st_size > MAX_FILE or
                    report['bytesInspected'] + before.st_size > max_bytes):
                raise Blocked('Module/time/byte budget reached; collection is incomplete')
            item = {'relativePath': binary.relative_to(app).as_posix()}
            try:
                with tempfile.TemporaryDirectory(prefix='fstr-static-worker-') as directory:
                    item['inspection'] = inspector(binary, Path(directory), max(0.1, min(30, remaining)))
                _, after = regular_read(binary, app, 4)
                require((before.st_ino, before.st_size, before.st_mtime_ns) ==
                        (after.st_ino, after.st_size, after.st_mtime_ns), 'Module changed during collection')
                item['status'] = 'PASS'
                report['bytesInspected'] += before.st_size
            except subprocess.TimeoutExpired:
                item.update(status='BLOCKED', reason='Inspector timeout; only owned worker stopped')
                report['collectionStatus'] = 'BLOCKED'
            except (OSError, ValueError):
                item.update(status='FAIL', reason='Module inspection failed; no absence conclusion allowed')
                report['collectionStatus'] = 'FAIL'
            report['modules'].append(item)
        # Do not combine records from an application update in progress.
        if identity(app)[2] != meta:
            raise ValueError('Application metadata changed during collection')
    except Blocked as error:
        if report['collectionStatus'] != 'FAIL':
            report['collectionStatus'] = 'BLOCKED'
        report['limits'].append(str(error))
    report['scanLimited'] = any(
        item.get('inspection', {}).get('stringScanLimited', True) or
        any(s['symbolsLimited'] for s in item.get('inspection', {}).get('slices', []))
        for item in report['modules'])
    report['limitations'] = ['Names and strings are leads only, not notification evidence.',
        'Symbols/strings are bounded; stripped/no-match modules do not prove absence.',
        'External/shared/late-loaded modules are not enumerated from a process.',
        'Cross-references, post-commit delivery, all-origin coverage and performance remain NOT RUN.',
        'Metadata is not code-signature or runtime verification. No AE process was launched or attached.']
    return report


def verify_kit(directory):
    manifest = json.loads((directory / 'build-manifest.json').read_text(encoding='utf-8'))
    require(manifest.get('sourceState') == 'clean' and
            re.fullmatch(r'[a-f0-9]{40}', manifest.get('sourceCommit', '')), 'Missing clean source identity')
    require(set(manifest.get('files', {})) == set(TOOLS), 'Wrong diagnostic kit file set')
    for name in TOOLS:
        path = directory / name
        require(not path.is_symlink() and path.is_file() and
                hashlib.sha256(path.read_bytes()).hexdigest() == manifest['files'][name], 'Diagnostic kit hash mismatch')
    return manifest


def save_report(report, output, manifest):
    output = output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:12]
    report = redact(dict(report, testRunId=run_id, collectorBuild=manifest))
    archive = output / ('FSTR-AE-Static-' + run_id + '.zip')
    fd = os.open(archive, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as package:
            package.writestr('report.json', json.dumps(report, indent=2, ensure_ascii=True) + '\n')
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    with Path(str(archive) + '.sha256').open('x', encoding='utf-8') as stream:
        stream.write(digest + '  ' + archive.name + '\n')
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', type=Path)
    parser.add_argument('--output', type=Path, default=Path.home() / 'Desktop/FSTR-AE-Research')
    args = parser.parse_args()
    try:
        manifest = verify_kit(Path(__file__).resolve().parent)
    except (OSError, ValueError):
        print('FAIL: missing or changed diagnostic kit. Nothing scanned.', file=sys.stderr)
        return 2
    try:
        if platform.system() != 'Darwin':
            raise Blocked('This launcher requires macOS; After Effects was not accessed')
        app = args.app or discover([Path('/Applications'), Path.home() / 'Applications'])
        target = app.resolve()
        if args.output.expanduser().resolve().is_relative_to(target):
            raise Blocked('Output cannot be placed inside the application')
        report = collect(app)
    except Blocked as error:
        report = {'collectionStatus': 'BLOCKED', 'reason': str(error), 'SYNC-001': 'NOT RUN'}
    except (OSError, ValueError, plistlib.InvalidFileException):
        report = {'collectionStatus': 'FAIL', 'reason': 'Invalid or inaccessible application input', 'SYNC-001': 'NOT RUN'}
    try:
        archive = save_report(report, args.output, manifest)
    except OSError:
        print('BLOCKED: report could not be written to the chosen output directory.', file=sys.stderr)
        return 2
    print(report['collectionStatus'] + ': ' + str(archive))
    print('Direct AE notifications: NOT RUN. No project, plug-in, preference or security setting changed.')
    return 0 if report['collectionStatus'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
