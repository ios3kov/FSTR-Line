"""LLDB controller for an already-running, explicitly identified AE test process."""
from __future__ import annotations
import json, time, uuid
from pathlib import Path
import lldb
import trace_callback
import runtime_protocol

# The launcher starts a fresh LLDB batch process for each capture. Keep its
# target alive until that debugger exits and has stopped its event handler.
_run_started = False

def _write(path,data):
    with Path(path).open('x',encoding='utf-8') as f:
        json.dump(data,f,indent=2,ensure_ascii=True); f.write('\n')

def _module_by_path(target,path):
    wanted=Path(path).resolve()
    for i in range(target.GetNumModules()):
        module=target.GetModuleAtIndex(i)
        spec=module.GetFileSpec()
        full=Path(spec.GetDirectory() or '')/(spec.GetFilename() or '')
        try:
            if full.resolve()==wanted:
                return module
        except OSError:
            pass
    return None

def _create_breakpoint(target,module,module_name,item):
    if 'fileAddress' in item:
        file_address=int(str(item['fileAddress']),0)
        address=module.ResolveFileAddress(file_address)
        if not address.IsValid() or address.GetFileAddress()!=file_address:
            raise RuntimeError('Could not resolve exact file address: '+item['label'])
        bp=target.BreakpointCreateBySBAddress(address)
        return bp,{'fileAddress':hex(file_address),'resolvedFileAddress':hex(address.GetFileAddress())}
    if 'regex' in item:
        bp=target.BreakpointCreateByRegex(item['regex'],module_name)
        return bp,{'regex':item['regex']}
    raise RuntimeError('Breakpoint has neither fileAddress nor regex: '+item['label'])

def _ack(path,kind,sequence=0,**extra):
    runtime_protocol.append_jsonl(path,dict(kind=kind,sequence=sequence,**extra))

def _stage(plan, result, label):
    """Opt-in file progress; never call LLDB or prevent detach on a logging error."""
    if not plan.get('diagnosticStages', False):
        return
    result['lastDiagnosticStage'] = label
    try:
        _ack(plan['ackPath'], 'controller-stage', stage=label,
             diagnosticErrorCount=len(result.get('diagnosticErrors', [])),
             monotonicNs=time.monotonic_ns())
    except Exception as error:
        errors = result.setdefault('diagnosticErrors', [])
        if len(errors) < 64:
            errors.append({'stage': label, 'errorType': type(error).__name__})


# Inner wait is shorter than the existing parent's exit deadline. Native SB calls
# still rely on that parent watchdog; this is not a guarantee against all hangs.
_STOP_WAIT_SECONDS = 5.0


def _pause_for_detach(debugger, process, plan, result, prefix='shutdown'):
    """Request interruption without synchronous Stop/Halt; never call target code."""
    _stage(plan, result, prefix + '-pause-begin')
    debugger.SetAsync(True)
    # A late breakpoint callback must not auto-resume a stop during teardown.
    # This only changes logger control state, not AE state or coverage claims.
    trace_callback.prepare_shutdown()
    deadline = time.monotonic() + _STOP_WAIT_SECONDS
    state = process.GetState()
    if state != lldb.eStateStopped:
        if state not in (lldb.eStateRunning, lldb.eStateStepping):
            raise RuntimeError('Target is not running or stopped before detach')
        _stage(plan, result, prefix + '-interrupt-begin')
        process.SendAsyncInterrupt()
        _stage(plan, result, prefix + '-interrupt-sent')
        while True:
            if time.monotonic() >= deadline:
                raise RuntimeError('Timed out confirming target stop before detach')
            state = process.GetState()
            if state == lldb.eStateStopped:
                break
            if state not in (lldb.eStateRunning, lldb.eStateStepping):
                raise RuntimeError('Target ended or changed state while stopping')
            # Yield to the debugger's event/callback thread. No AE-state polling.
            time.sleep(0.01)
    if time.monotonic() >= deadline:
        raise RuntimeError('Stop confirmation arrived after its deadline')
    result['stopConfirmed'] = True
    _stage(plan, result, prefix + '-stop-confirmed')

def run(debugger,plan_name):
    global _run_started
    if _run_started:
        raise RuntimeError('A capture requires a fresh dedicated LLDB process')
    _run_started = True
    plan=json.loads(Path(plan_name).read_text(encoding='utf-8'))
    result_path=Path(plan['resultPath']); trace_path=Path(plan['tracePath'])
    control_path=Path(plan['controlPath']); ack_path=Path(plan['ackPath'])
    result={'status':'FAIL',
            'scope':'observational LLDB breakpoint trace; terminal interaction stays in parent launcher',
            'SYNC-001':'NOT RUN','pid':plan.get('pid'),'breakpoints':[],'detached':False,
            'interactive':True}
    target=None; process=None; attached=False
    pause_attempted=False; detach_attempted=False
    debugger.SetAsync(False)
    try:
        _stage(plan, result, 'create-target-begin')
        target=debugger.CreateTarget(plan['executable'])
        if not target.IsValid():
            raise RuntimeError('LLDB could not create target')
        _stage(plan, result, 'attach-begin')
        error=lldb.SBError()
        process=target.AttachToProcessWithID(debugger.GetListener(),int(plan['pid']),error)
        if error.Fail() or not process.IsValid():
            result.update(status='BLOCKED',stage='attach',error=error.GetCString() or 'Attach failed')
            _write(result_path,result); return
        attached=True
        _stage(plan, result, 'attach-end')
        module_map={}; modules={}; module_names={}; bp_meta={}
        for item in plan['modules']:
            module=_module_by_path(target,item['path'])
            if module is None or not module.IsValid():
                raise RuntimeError('Required module is not loaded: '+item['key'])
            actual_uuid=str(uuid.UUID(module.GetUUIDString())).lower()
            expected=str(uuid.UUID(item['uuid'])).lower()
            if actual_uuid!=expected:
                raise RuntimeError('Loaded module UUID mismatch: '+item['key'])
            module_map[actual_uuid]=item['sha256']; modules[item['key']]=module
            module_names[item['key']]=Path(item['path']).name
        for item in plan['breakpoints']:
            key=item['module']
            if key not in modules:
                raise RuntimeError('Unknown breakpoint module: '+key)
            bp,identity=_create_breakpoint(target,modules[key],module_names[key],item)
            count=bp.GetNumLocations()
            row={'id':bp.GetID(),'label':item['label'],'role':item.get('role','candidate'),
                 'module':key,'locations':count,**identity}
            result['breakpoints'].append(row)
            if count<int(item['minLocations']) or count>int(item['maxLocations']):
                raise RuntimeError('Breakpoint location count outside declared bounds: '+item['label'])
            bp.SetScriptCallbackFunction('trace_callback.on_breakpoint')
            bp_meta[bp.GetID()]={'label':item['label'],'role':item.get('role','candidate')}
            if 'contextRegister' in item:
                bp_meta[bp.GetID()]['contextRegister']=item['contextRegister']

        trace_callback.start_capture(trace_path,plan['runId'],int(plan['pid']),module_map,
                                     breakpoints=bp_meta,max_events=int(plan.get('maxEvents',5000)),
                                     max_seconds=int(plan['durationSeconds'])+30,
                                     max_frames=int(plan.get('maxFrames',8)))
        trace_callback.mark_phase('attach-verified')
        debugger.SetAsync(True)
        cont=process.Continue()
        if cont.Fail():
            raise RuntimeError('Could not continue attached process: '+str(cont))
        _ack(ack_path,'ready',0)

        expected_sequence=1
        deadline=time.monotonic()+float(plan['durationSeconds'])
        finished=False
        aborted=False
        with control_path.open('r',encoding='utf-8') as control:
            while time.monotonic()<deadline:
                line=control.readline()
                if not line:
                    state=process.GetState()
                    if state in (lldb.eStateExited,lldb.eStateCrashed,lldb.eStateDetached):
                        raise RuntimeError('Target process ended during interactive capture')
                    time.sleep(0.05)
                    continue
                row=json.loads(line)
                if not isinstance(row,dict):
                    raise RuntimeError('Invalid control row')
                sequence=int(row.get('sequence',0))
                if sequence!=expected_sequence:
                    raise RuntimeError('Control sequence mismatch')
                kind=row.get('kind')
                if kind=='phase':
                    label=row.get('label')
                    trace_callback.mark_phase(label)
                    _ack(ack_path,'phase-ack',sequence,label=label)
                elif kind=='finish':
                    trace_callback.mark_phase('capture-finished')
                    _ack(ack_path,'finish-ack',sequence)
                    finished=True
                    break
                elif kind=='abort':
                    trace_callback.mark_phase('capture-aborted')
                    _ack(ack_path,'abort-ack',sequence)
                    aborted=True
                    break
                else:
                    raise RuntimeError('Unknown control command')
                expected_sequence+=1
            else:
                raise RuntimeError('Interactive control protocol timed out')

        pause_attempted=True
        _pause_for_detach(debugger, process, plan, result)
        _stage(plan, result, 'detach-begin')
        detach_attempted=True
        detach_error=process.Detach(False)
        _stage(plan, result, 'detach-end')
        if detach_error.Fail():
            raise RuntimeError('Detach failed: '+str(detach_error))
        attached=False
        _stage(plan, result, 'capture-close-begin')
        trace_callback.stop_capture()
        _stage(plan, result, 'capture-close-end')
        if finished and not aborted:
            result.update(status='PASS',stage='complete',detached=True,
                          note='PASS means observer ran and detached, not notification coverage.')
        else:
            result.update(status='BLOCKED',stage='aborted',detached=True,
                          note='Interactive capture aborted before completion.')
        if result.get('diagnosticErrors'):
            result.update(status='FAIL', stage='diagnostics')
        _stage(plan, result, 'result-write-begin')
        _write(result_path,result)
        _stage(plan, result, 'result-write-end')
    except Exception as error:
        _stage(plan, result, 'exception-cleanup-begin')
        result.update(status='FAIL' if attached else result.get('status','FAIL'),
                      stage=result.get('stage','runtime'),error=str(error))
        if attached and process and process.IsValid():
            try:
                # Do not retry an unconfirmed stop through blocking Detach/Stop.
                # Preserve FAIL; the parent separately records cleanup/exit.
                if not pause_attempted:
                    pause_attempted=True
                    _pause_for_detach(debugger, process, plan, result, 'recovery')
                if result.get('stopConfirmed') is not True:
                    raise RuntimeError('Detach not attempted without confirmed stop')
                if detach_attempted:
                    raise RuntimeError('Failed detach is not retried')
                _stage(plan, result, 'recovery-detach-begin')
                detach_attempted=True
                detach_error=process.Detach(False)
                _stage(plan, result, 'recovery-detach-end')
                result['detached']=not detach_error.Fail()
                if result['detached']:
                    attached=False
            except Exception as detach_problem:
                result['detachError']=str(detach_problem)
        try: _write(result_path,result)
        except FileExistsError: pass
    finally:
        _stage(plan, result, 'finally-capture-close-begin')
        trace_callback.stop_capture()
        _stage(plan, result, 'finally-capture-close-end')
        # Do not destroy the Target while the CLI's event thread may still
        # consume detached/stopped events referring to its Process. The target
        # list owns it until normal debugger teardown; one capture per process
        # bounds this lifetime. Parent acceptance also requires exit code zero.
        _stage(plan, result, 'target-retained-for-debugger-exit')
        _stage(plan, result, 'controller-return')
