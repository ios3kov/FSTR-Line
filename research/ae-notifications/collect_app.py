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


class DiscoveryBlocked(Blocked):
    def __init__(self, message, audit):
        super().__init__(message)
        self.audit = audit


# Standard Additions opens a file chooser, not the selected application.
# No Finder/System Events automation, target launch or permission changes.
CHOOSE_APP_SCRIPT = """try
    set chosen to choose file with prompt "Select your installed After Effects 25.6 application (.app)" of type {"com.apple.application-bundle"}
    return POSIX path of chosen
on error number -128
    return "__FSTR_SELECTION_CANCELLED__"
end try
"""


def choose_app(runner=subprocess.run):
    try:
        result = runner(['/usr/bin/osascript', '-e', CHOOSE_APP_SCRIPT],
                        capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        raise Blocked('Application selection timed out; no application was scanned') from None
    except OSError:
        raise Blocked('Application chooser unavailable; use --app with the exact .app path') from None
    if result.returncode:
        raise Blocked('Application chooser failed; use --app with the exact .app path')
    selected = result.stdout.rstrip('\r\n')
    if selected == '__FSTR_SELECTION_CANCELLED__':
        raise Blocked('Application selection cancelled; no application was scanned')
    if not selected or '\0' in selected or not Path(selected).is_absolute():
        raise Blocked('Application chooser returned no valid absolute path')
    return Path(selected)


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
    # Exact identifier observed in the user's AE 25.6.0.101 report; no prefix match.
    if bundle != 'com.adobe.AfterEffects.application':
        raise Blocked('Bundle identifier does not match the expected After Effects identifier; see selection metadata')
    if not isinstance(version, str) or not re.match(r'^25\.6(?:\.|$)', version):
        raise Blocked('Application version does not match the 25.6 collection target; see selection metadata')
    require(isinstance(executable, str) and executable not in ('', '.', '..') and
            Path(executable).name == executable and '\\' not in executable, 'Invalid executable name')
    binary = app / 'Contents/MacOS' / executable
    magic, _ = regular_read(binary, app, 4)
    require(magic in MAGICS, 'Main executable is not Mach-O')
    return app, binary, {'bundleId': bundle, 'shortVersion': version,
        'bundleVersion': str(values.get('CFBundleVersion', 'unknown')),
        'plistSha256': hashlib.sha256(raw).hexdigest(),
        'runtimeIdentityVerified': False, 'exactBuild101Verified': False}


def candidate_details(candidate):
    """Retain only allowlisted metadata, including why this candidate was rejected."""
    details = {'appName': candidate.name, 'status': 'NOT VALIDATED', 'metadata': {}}
    try:
        require(not candidate.is_symlink() and candidate.is_dir(), 'Not an actual application directory')
        app = candidate.resolve(strict=True)
        raw, info = regular_read(app / 'Contents/Info.plist', app, 1024 * 1024 + 1)
        require(info.st_size <= 1024 * 1024, 'Oversized Info.plist')
        values = plistlib.loads(raw)
        require(isinstance(values, dict), 'Invalid Info.plist')
        for key in ('CFBundleIdentifier', 'CFBundleShortVersionString',
                    'CFBundleVersion', 'CFBundleExecutable'):
            value = values.get(key)
            details['metadata'][key] = value[:256] if isinstance(value, str) else None
        identity(candidate)
        details['status'] = 'ACCEPTED'
    except (OSError, ValueError, Blocked, plistlib.InvalidFileException) as error:
        details.update(status='REJECTED', reason=str(error)[:1024], errorType=type(error).__name__)
    return details


def discover(roots, audit=None):
    """Bounded automatic discovery; retain rejection reasons instead of hiding them."""
    audit = {} if audit is None else audit
    audit.update(status='SEARCHING', roots=[], candidates=[], supportedCandidateCount=0)
    found = []
    incomplete = False
    for root in roots:
        root_record = {'directory': str(root), 'status': 'SCANNED'}
        audit['roots'].append(root_record)
        if not root.exists():
            root_record['status'] = 'MISSING'
            continue
        if not root.is_dir() or root.is_symlink():
            root_record['status'] = 'REJECTED'
            incomplete = True
            continue
        try:
            # Read at most limit+1 entries, not an unbounded sorted directory.
            with os.scandir(root) as entries:
                items = []
                for entry in entries:
                    if len(items) == 1000:
                        incomplete = True
                        root_record['status'] = 'LIMIT_REACHED'
                        break
                    items.append(Path(entry.path))
            for item in sorted(items):
                candidates = [item] if item.suffix.lower() == '.app' else []
                if item.is_dir() and not item.is_symlink() and item.name.lower().startswith('adobe after effects'):
                    with os.scandir(item) as children:
                        examined = 0
                        for entry in children:
                            examined += 1
                            if examined > 1000:
                                incomplete = True
                                root_record['status'] = 'LIMIT_REACHED'
                                break
                            if Path(entry.name).suffix.lower() == '.app':
                                if len(candidates) == 20:
                                    incomplete = True
                                    root_record['status'] = 'LIMIT_REACHED'
                                    break
                                candidates.append(Path(entry.path))
                for candidate in candidates:
                    try:
                        app, _, _ = identity(candidate)
                        if app not in found:
                            found.append(app)
                            audit['candidates'].append(candidate_details(candidate))
                    except (OSError, ValueError, Blocked, plistlib.InvalidFileException):
                        # Do not emit a user's unrelated installed-app inventory.
                        if 'after effects' in str(candidate.relative_to(root)).lower():
                            audit['candidates'].append(candidate_details(candidate))
        except OSError as error:
            incomplete = True
            root_record.update(status='UNREADABLE', errorType=type(error).__name__)
    audit['supportedCandidateCount'] = len(found)
    audit['status'] = 'INCOMPLETE' if incomplete else ('FOUND' if len(found) == 1 else 'AMBIGUOUS' if found else 'NOT_FOUND')
    if incomplete or len(found) != 1:
        raise DiscoveryBlocked('Automatic AE discovery: ' + audit['status'] + '. Select the exact application.', audit)
    return found[0]


def scan_files(app, main, max_files):
    yield main
    count = 0
    def unreadable_directory(error):
        raise Blocked('An application directory could not be enumerated') from error
    for directory, dirs, files in os.walk(app / 'Contents', followlinks=False, onerror=unreadable_directory):
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
        'modules': [], 'limits': [], 'bytesBudgetCharged': 0,
        'environment': {'system': platform.system(), 'release': platform.release(),
                        'machine': platform.machine(), 'python': platform.python_version()}}
    started = time.monotonic()
    try:
        for binary in scan_files(app, main, max_files):
            remaining = max_seconds - (time.monotonic() - started)
            _, before = regular_read(binary, app, 4)
            if (remaining <= 0 or len(report['modules']) >= max_modules or before.st_size > MAX_FILE or
                    report['bytesBudgetCharged'] + before.st_size > max_bytes):
                raise Blocked('Module/time/byte budget reached; collection is incomplete')
            item = {'relativePath': binary.relative_to(app).as_posix()}
            # Reserve the full input even if its worker fails or times out.
            report['bytesBudgetCharged'] += before.st_size
            try:
                with tempfile.TemporaryDirectory(prefix='fstr-static-worker-') as directory:
                    item['inspection'] = inspector(binary, Path(directory), max(0.1, min(30, remaining)))
                _, after = regular_read(binary, app, 4)
                require((before.st_ino, before.st_size, before.st_mtime_ns) ==
                        (after.st_ino, after.st_size, after.st_mtime_ns), 'Module changed during collection')
                item['status'] = 'PASS'
            except subprocess.TimeoutExpired:
                item.update(status='BLOCKED', reason='Inspector timeout; only owned worker stopped')
                if report['collectionStatus'] != 'FAIL':
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    selection_args = parser.add_mutually_exclusive_group()
    selection_args.add_argument('--app', type=Path)
    selection_args.add_argument('--choose-app', action='store_true', help='Choose the exact installed .app in a macOS dialog')
    parser.add_argument('--non-interactive', action='store_true', help='Never open a chooser; save all discovery failures')
    parser.add_argument('--output', type=Path, default=Path.home() / 'Desktop/FSTR-AE-Research')
    args = parser.parse_args(argv)
    if args.choose_app and args.non_interactive:
        parser.error('--choose-app and --non-interactive cannot be combined')
    try:
        manifest = verify_kit(Path(__file__).resolve().parent)
    except (OSError, ValueError):
        print('FAIL: missing or changed diagnostic kit. Nothing scanned.', file=sys.stderr)
        return 2
    selection = {'mode': 'explicit' if args.app else 'chooser' if args.choose_app else 'automatic'}
    try:
        if platform.system() != 'Darwin':
            raise Blocked('This launcher requires macOS; After Effects was not accessed')
        if args.app is not None:
            app = args.app.expanduser()
        elif args.choose_app:
            app = choose_app()
        else:
            audit = {}
            selection['discovery'] = audit
            try:
                app = discover([Path('/Applications'), Path.home() / 'Applications'], audit)
            except DiscoveryBlocked:
                if args.non_interactive:
                    raise
                selection['mode'] = 'chooser-after-discovery'
                app = choose_app()
        selection['candidate'] = candidate_details(app)
        target = app.resolve()
        if args.output.expanduser().resolve().is_relative_to(target):
            raise Blocked('Output cannot be placed inside the application')
        report = collect(app)
    except Blocked as error:
        report = {'collectionStatus': 'BLOCKED', 'reason': str(error), 'SYNC-001': 'NOT RUN'}
    except (OSError, ValueError, plistlib.InvalidFileException) as error:
        report = {'collectionStatus': 'FAIL', 'reason': str(error)[:1024],
                  'errorType': type(error).__name__, 'SYNC-001': 'NOT RUN'}
    report['selection'] = selection
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
