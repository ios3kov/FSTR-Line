"""Opt-in LLDB callback logger. Does not attach, create breakpoints or evaluate target code."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import threading
import time
import uuid

_lock = threading.RLock()
_capture = None


def start_capture(path, run_id, expected_pid, modules, max_events=1000, max_seconds=60):
    """modules maps exact loaded module UUIDs to previously measured SHA-256 values."""
    global _capture
    if not isinstance(run_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', run_id):
        raise ValueError('Invalid run ID')
    if not isinstance(expected_pid, int) or expected_pid <= 0:
        raise ValueError('An explicit test-process PID is required')
    if not 1 <= max_events <= 10000 or not 1 <= max_seconds <= 600:
        raise ValueError('Capture bounds exceeded')
    if not modules or len(modules) > 64:
        raise ValueError('Exact identified modules are required')
    normalized = {}
    for module_uuid, digest in modules.items():
        if not re.fullmatch(r'[a-f0-9]{64}', digest):
            raise ValueError('Invalid module digest')
        normalized[str(uuid.UUID(module_uuid)).lower()] = digest
    with _lock:
        if _capture is not None:
            raise RuntimeError('A capture is already active')
        fd = os.open(Path(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        stream = os.fdopen(fd, 'w', encoding='utf-8')
        _capture = {'stream': stream, 'runId': run_id, 'pid': expected_pid,
                    'modules': normalized, 'started': time.monotonic_ns(), 'sequence': 0,
                    'hits': 0, 'maxEvents': max_events, 'maxNs': int(max_seconds * 1e9), 'stopped': False}
        _write({'kind': 'capture-start', 'moduleIdentities': normalized,
                'moduleHashesIndependentlyVerifiedByLogger': False})


def _write(fields):
    _capture['sequence'] += 1
    row = dict(fields, testRunId=_capture['runId'], sequence=_capture['sequence'],
               monotonicNs=time.monotonic_ns(), wallTimeNs=time.time_ns())
    _capture['stream'].write(json.dumps(row, ensure_ascii=True) + '\n')
    _capture['stream'].flush()


def on_breakpoint(frame, bp_loc, internal_dict):
    """False resumes after this breakpoint; True pauses. Never calls EvaluateExpression."""
    with _lock:
        if _capture is None or _capture['stopped']:
            return True
        try:
            if (_capture['hits'] >= _capture['maxEvents'] or
                    time.monotonic_ns() - _capture['started'] >= _capture['maxNs']):
                _capture['stopped'] = True
                _write({'kind': 'capture-limit', 'pauseRequested': True})
                return True
            thread = frame.GetThread()
            process = thread.GetProcess()
            if process.GetProcessID() != _capture['pid']:
                raise ValueError('Unexpected process PID')
            address = frame.GetPCAddress()
            module_uuid = str(uuid.UUID(address.GetModule().GetUUIDString())).lower()
            if module_uuid not in _capture['modules']:
                raise ValueError('Unidentified module UUID')
            _capture['hits'] += 1
            _write({'kind': 'candidate-hit', 'source': 'lldb-breakpoint', 'commitPhase': 'UNKNOWN',
                    'pid': _capture['pid'], 'threadId': thread.GetThreadID(),
                    'breakpointId': bp_loc.GetBreakpoint().GetID(), 'locationId': bp_loc.GetID(),
                    'moduleUUID': module_uuid, 'unslidAddress': hex(address.GetFileAddress()),
                    'function': frame.GetFunctionName(), 'isNotificationProven': False})
            return False
        except Exception as error:
            _capture['stopped'] = True
            try:
                _write({'kind': 'capture-error', 'error': str(error), 'pauseRequested': True})
            except Exception:
                pass
            return True


def stop_capture():
    global _capture
    with _lock:
        if _capture is not None:
            try:
                _write({'kind': 'capture-end', 'hits': _capture['hits'], 'SYNC-001': 'NOT RUN'})
            finally:
                _capture['stream'].close()
                _capture = None
