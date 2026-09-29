"""LLDB controller for an already-running, explicitly identified AE test process."""
from __future__ import annotations
import json, time, uuid
from pathlib import Path
import lldb
import trace_callback
import runtime_protocol

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

def run(debugger,plan_name):
    plan=json.loads(Path(plan_name).read_text(encoding='utf-8'))
    result_path=Path(plan['resultPath']); trace_path=Path(plan['tracePath'])
    control_path=Path(plan['controlPath']); ack_path=Path(plan['ackPath'])
    result={'status':'FAIL',
            'scope':'observational LLDB breakpoint trace; terminal interaction stays in parent launcher',
            'SYNC-001':'NOT RUN','pid':plan.get('pid'),'breakpoints':[],'detached':False,
            'interactive':True}
    target=None; process=None; attached=False; capture_started=False
    debugger.SetAsync(False)
    try:
        target=debugger.CreateTarget(plan['executable'])
        if not target.IsValid():
            raise RuntimeError('LLDB could not create target')
        error=lldb.SBError()
        process=target.AttachToProcessWithID(debugger.GetListener(),int(plan['pid']),error)
        if error.Fail() or not process.IsValid():
            result.update(status='BLOCKED',stage='attach',error=error.GetCString() or 'Attach failed')
            _write(result_path,result); return
        attached=True
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

        trace_callback.start_capture(trace_path,plan['runId'],int(plan['pid']),module_map,
                                     breakpoints=bp_meta,max_events=int(plan.get('maxEvents',5000)),
                                     max_seconds=int(plan['durationSeconds'])+30,
                                     max_frames=int(plan.get('maxFrames',8)))
        capture_started=True
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

        debugger.SetAsync(False)
        if process.GetState()==lldb.eStateRunning:
            stop_error=process.Stop()
            if stop_error.Fail():
                raise RuntimeError('Could not pause process for clean detach: '+str(stop_error))
        trace_callback.stop_capture(); capture_started=False
        detach_error=process.Detach()
        if detach_error.Fail():
            raise RuntimeError('Detach failed: '+str(detach_error))
        attached=False
        if finished and not aborted:
            result.update(status='PASS',stage='complete',detached=True,
                          note='PASS means observer ran and detached, not notification coverage.')
        else:
            result.update(status='BLOCKED',stage='aborted',detached=True,
                          note='Interactive capture aborted before completion.')
        _write(result_path,result)
    except Exception as error:
        if capture_started:
            try: trace_callback.stop_capture()
            except Exception: pass
        result.update(status='FAIL' if attached else result.get('status','FAIL'),
                      stage=result.get('stage','runtime'),error=str(error))
        if attached and process and process.IsValid():
            try:
                debugger.SetAsync(False)
                if process.GetState()==lldb.eStateRunning:
                    process.Stop()
                detach_error=process.Detach()
                result['detached']=not detach_error.Fail(); attached=False
            except Exception as detach_problem:
                result['detachError']=str(detach_problem)
        try: _write(result_path,result)
        except FileExistsError: pass
    finally:
        trace_callback.stop_capture()
        if target and target.IsValid():
            debugger.DeleteTarget(target)
