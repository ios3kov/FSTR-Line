"""Liveness oracle for a test-owned child only. Never discovers or signals AE."""
from __future__ import annotations
import os
import stat
import time
from pathlib import Path

# Test-only finite program; the counter is written by the target itself, not LLDB.
SOURCE = '''#include <unistd.h>
#include <fcntl.h>
#include <stdint.h>
extern "C" __attribute__((noinline)) void fstr_runtime_candidate(){}
int main(int argc, char **argv) {
    if (argc != 2) return 2;
    int fd = open(argv[1], O_CREAT | O_EXCL | O_WRONLY, 0600);
    if (fd < 0) return 3;
    for (uint64_t i = 1; i <= 2000; ++i) {
        fstr_runtime_candidate();
        if (pwrite(fd, &i, sizeof(i), 0) != sizeof(i)) return 4;
        usleep(20000);
    }
    return close(fd) == 0 ? 0 : 5;
}
'''


def _counter(path: Path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(fd, 'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError('Fixture counter must be a regular file')
            raw = stream.read(9)
    except FileNotFoundError:
        return None
    if len(raw) != 8:
        raise ValueError('Fixture counter must contain exactly eight bytes')
    return int.from_bytes(raw, 'little')


def require_progress(process, path: Path, *, timeout=1.0):
    """Require fresh target-written progress and a live child, without resuming it."""
    if not 0 < timeout <= 5:
        raise ValueError('Invalid fixture progress deadline')
    start = None
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError('Owned fixture exited before liveness acceptance')
        value = _counter(path)
        if value is not None:
            if start is None:
                start = value
            elif value < start:
                raise RuntimeError('Owned fixture counter regressed')
            elif value > start:
                if process.poll() is not None:
                    raise RuntimeError('Owned fixture exited during liveness acceptance')
                return {'status': 'PASS', 'before': start, 'after': value,
                        'oracle': 'target-written-counter', 'resumedByTest': False}
        time.sleep(0.01)
    raise RuntimeError('Owned fixture did not progress before liveness deadline')
