"""Run only the owned C++ fixture under actual LLDB; never attach to AE."""
import hashlib
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True


def run(debugger, binary_name, result_name, repo_root):
    import lldb
    sys.path.insert(0, str(Path(repo_root) / 'research/ae-notifications'))
    import trace_callback
    binary = Path(binary_name).resolve(strict=True)
    result = Path(result_name)
    if binary.name != 'fstr-owned-fixture' or result.exists():
        raise RuntimeError('Owned fixture and fresh result required')
    debugger.SetAsync(False)
    target = debugger.CreateTarget(str(binary))
    if not target.IsValid():
        raise RuntimeError('LLDB could not create fixture target')
    main = target.BreakpointCreateByName('main', binary.name)
    hook = target.BreakpointCreateByName('fstr_fixture_notification', binary.name)
    if main.GetNumLocations() != 1 or hook.GetNumLocations() != 1:
        raise RuntimeError('Expected unique fixture breakpoint locations')
    hook.SetScriptCallbackFunction('trace_callback.on_breakpoint')
    process = None
    trace_path = result.with_suffix('.jsonl')
    try:
        process = target.LaunchSimple(None, None, str(binary.parent))
        if not process.IsValid() or process.GetState() != lldb.eStateStopped:
            raise RuntimeError('Owned fixture launch/initial stop failed')
        target.BreakpointDelete(main.GetID())
        module = target.FindModule(lldb.SBFileSpec(str(binary)))
        module_uuid = module.GetUUIDString()
        digest = hashlib.sha256(binary.read_bytes()).hexdigest()
        trace_callback.start_capture(trace_path, 'lldb-owned-positive-control',
                                     process.GetProcessID(), {module_uuid: digest})
        error = process.Continue()
        if error.Fail() or process.GetState() != lldb.eStateExited or process.GetExitStatus() != 0:
            raise RuntimeError('Fixture did not exit normally after callback delivery')
        trace_callback.stop_capture()
        rows = [json.loads(line) for line in trace_path.read_text().splitlines()]
        hits = [row for row in rows if row['kind'] == 'candidate-hit']
        if len(hits) != 3 or any(row['isNotificationProven'] or row['commitPhase'] != 'UNKNOWN' for row in hits):
            raise RuntimeError('Positive-control callback contract failed')
        with result.open('x', encoding='utf-8') as stream:
            json.dump({'status': 'PASS', 'scope': 'owned C++ fixture under real LLDB, NOT Adobe AE',
                       'hitsExpected': 3, 'hitsObserved': len(hits), 'moduleUUID': module_uuid,
                       'fixtureSha256': digest, 'SYNC-001': 'NOT RUN'}, stream, indent=2)
    finally:
        trace_callback.stop_capture()
        # Only the process launched by this function, never an existing session.
        if process and process.IsValid() and process.GetState() not in (lldb.eStateExited, lldb.eStateDetached):
            process.Kill()
        debugger.DeleteTarget(target)
