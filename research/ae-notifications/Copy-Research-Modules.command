#!/bin/bash
# Copy data only: no Adobe execution, debugger, install, network or project access.
set -euo pipefail
exec python3 -I -B - "$0" "$@" <<'PY'
import argparse, hashlib, json, os, stat, sys, tempfile, zipfile
from datetime import datetime, timezone
from pathlib import Path

MODULES = {
    'BEE.dylib': 'BEE.dylib',
    'AfterFXLib': 'AfterFXLib.framework/Versions/A/AfterFXLib',
    'dvacore': 'dvacore.framework/Versions/A/dvacore',
}
LIMIT = 1024 * 1024 * 1024
CHUNK = 1024 * 1024


def regular(path):
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, 'O_NOFOLLOW', 0))
    stream = os.fdopen(fd, 'rb')
    info = os.fstat(stream.fileno())
    if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= LIMIT:
        stream.close()
        raise ValueError('Not a nonempty bounded regular file: ' + path.name)
    return stream


def digest(stream, destination=None):
    value = hashlib.sha256()
    size = 0
    for chunk in iter(lambda: stream.read(CHUNK), b''):
        size += len(chunk)
        if size > LIMIT:
            raise ValueError('Module size limit exceeded')
        value.update(chunk)
        if destination is not None:
            destination.write(chunk)
    return {'sha256': value.hexdigest(), 'bytes': size}


def main():
    parser = argparse.ArgumentParser(description='Copy three AE libraries for offline research. No AE execution.')
    parser.add_argument('--app', type=Path, default=Path('/Applications/Adobe After Effects 2025/Adobe After Effects 2025.app'))
    parser.add_argument('--output', type=Path, default=Path.home() / 'Desktop/FSTR-AE-Research')
    args = parser.parse_args(sys.argv[2:])
    app = args.app.expanduser().resolve(strict=True)
    framework = app / 'Contents/Frameworks'
    sources, before = {}, {}
    for name, relative in MODULES.items():
        path = app
        for part in ('Contents', 'Frameworks', *Path(relative).parts):
            path = path / part
            if path.is_symlink():
                raise ValueError('Symlink source refused: ' + name)
        with regular(path) as stream:
            before[name] = digest(stream)
        sources[name] = path
    output = args.output.expanduser().resolve()
    if output == app or app in output.parents:
        raise ValueError('Output must be outside the application')
    output.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='FSTR-Source-Modules-', dir=output))
    partial = work / 'FSTR-AE-Modules.zip.partial'
    manifest = {'schemaVersion': 1, 'kind': 'offline-module-input',
                'copierSha256': hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest(),
                'capturedAtUtc': datetime.now(timezone.utc).isoformat(),
                'scope': 'Library bytes only; no project access or Adobe code execution',
                'buildCompatibility': 'NOT CHECKED; verify received hashes against research baseline',
                'SYNC-001': 'NOT RUN', 'modules': {}}
    with zipfile.ZipFile(partial, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, path in sources.items():
            with regular(path) as stream, archive.open(name, 'w', force_zip64=True) as destination:
                copied = digest(stream, destination)
            if copied != before[name]:
                raise ValueError('Module changed while copying: ' + name)
            manifest['modules'][name] = dict(copied, relativePath='Contents/Frameworks/' + MODULES[name])
        for name, path in sources.items():
            with regular(path) as stream:
                if digest(stream) != before[name]:
                    raise ValueError('Module changed during snapshot: ' + name)
        archive.writestr('manifest.json', json.dumps(manifest, indent=2) + '\n')
    with zipfile.ZipFile(partial) as archive:
        for name in MODULES:
            with archive.open(name) as stream:
                if digest(stream) != before[name]:
                    raise ValueError('Archive verification failed: ' + name)
    final = work / 'FSTR-AE-Modules.zip'
    partial.rename(final)
    with final.open('rb') as stream:
        value = hashlib.file_digest(stream, 'sha256').hexdigest() if hasattr(hashlib, 'file_digest') else None
    if value is None:
        h = hashlib.sha256()
        with final.open('rb') as stream:
            for chunk in iter(lambda: stream.read(CHUNK), b''):
                h.update(chunk)
        value = h.hexdigest()
    (work / 'SHA256.txt').write_text(value + '  ' + final.name + '\n', encoding='ascii')
    print(json.dumps({'status': 'COPIED', 'archive': str(final), 'sha256': value, 'SYNC-001': 'NOT RUN'}))
    print('Пришли FSTR-AE-Modules.zip из указанной папки. Проекты и настройки не копировались.')


os.umask(0o077)
try:
    main()
except Exception as error:
    print('BLOCKED: ' + str(error) + '. No completed snapshot is claimed.', file=sys.stderr)
    raise SystemExit(2)
PY
