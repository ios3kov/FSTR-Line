"""Bounded diagnostics and cleanup for test-owned subprocesses, never user AE."""
from __future__ import annotations

import hashlib
import json
import os
import signal
import stat
import subprocess
import tempfile
import threading
from pathlib import Path

MAX_LOG = 256 * 1024
FILES = ('plan.json', 'ack.jsonl', 'control.jsonl', 'trace.jsonl', 'result.json', 'lldb.log')


class BoundedLog:
    """Drain an owned child pipe continuously, retaining only a bounded prefix."""
    def __init__(self, pipe, path: Path):
        self.pipe = pipe
        self.path = path
        self.truncated = False
        self.error = None
        self.thread = threading.Thread(target=self._drain, daemon=True)
        self.thread.start()

    def _drain(self):
        kept = 0
        try:
            with self.path.open('xb') as dest:
                while True:
                    chunk = os.read(self.pipe.fileno(), 65536)
                    if not chunk:
                        break
                    payload = chunk[:max(0, MAX_LOG - kept)]
                    dest.write(payload)
                    dest.flush()
                    kept += len(payload)
                    self.truncated |= len(payload) < len(chunk)
        except Exception as error:
            self.error = type(error).__name__
        finally:
            self.pipe.close()

    def finish(self):
        self.thread.join(timeout=2)
        return {'complete': not self.thread.is_alive() and not self.truncated and self.error is None,
                'truncated': self.truncated, 'errorType': self.error,
                'readerStopped': not self.thread.is_alive()}


def reap_owned(process, *, resume=False):
    """Call only with a Popen object created by this test. No discovery or arbitrary PID."""
    if process is None:
        return {'reaped': True, 'action': 'not-started'}
    actions = []
    try:
        if process.poll() is None:
            actions.append('terminate')
            process.terminate()
            # A stopped fixture cannot handle SIGTERM until it is resumed.
            if resume and process.poll() is None:
                process.send_signal(signal.SIGCONT)
                actions.append('resume-owned-fixture')
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                actions.append('kill')
        code = process.wait(timeout=2)
        return {'reaped': True, 'actions': actions, 'exitCode': code}
    except (OSError, subprocess.SubprocessError) as error:
        return {'reaped': False, 'actions': actions, 'errorType': type(error).__name__}


def save_evidence(work: Path, output: Path, result: dict) -> Path:
    """Allowlisted regular files only; bound before decoding, never follow symlinks."""
    work = work.resolve()
    output.mkdir(parents=True, exist_ok=True)
    owned = Path(tempfile.mkdtemp(prefix='run-', dir=output))
    def redact(text):
        # Include macOS /var alias as well as its canonical /private/var spelling.
        aliases = {str(work), str(work).removeprefix('/private') if str(work).startswith('/private/') else str(work)}
        for alias in sorted(aliases, key=len, reverse=True):
            text = text.replace(alias, '<FIXTURE>')
        return text.replace(str(Path.home()), '<HOME>')
    files = {}
    for name in FILES:
        try:
            fd = os.open(work / name, os.O_RDONLY | os.O_NONBLOCK | getattr(os, 'O_NOFOLLOW', 0))
            with os.fdopen(fd, 'rb') as src:
                info = os.fstat(src.fileno())
                if not stat.S_ISREG(info.st_mode):
                    raise ValueError('not a regular file')
                data = src.read(MAX_LOG + 1)
            text = redact(data[:MAX_LOG].decode('utf-8', 'replace'))
            stored = text.encode('utf-8')
            files[name] = {'text': text, 'inputBytes': info.st_size,
                           'complete': info.st_size <= MAX_LOG and len(data) <= MAX_LOG,
                           'storedSha256': hashlib.sha256(stored).hexdigest()}
        except (OSError, ValueError) as error:
            files[name] = {'complete': False, 'errorType': type(error).__name__}
    report = {**result, 'runId': owned.name, 'files': files,
              'scope': 'owned fixture diagnostics; NOT Adobe AE', 'SYNC-001': 'NOT RUN'}
    payload = (json.dumps(report, ensure_ascii=True, indent=2) + '\n').encode()
    path = owned / 'summary.json'
    path.write_bytes(payload)
    (owned / 'SHA256.txt').write_text(hashlib.sha256(payload).hexdigest() + '  summary.json\n')
    return path
