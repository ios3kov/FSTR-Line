"""LLDB controller for an already-running, explicitly identified AE test process."""
from __future__ import annotations
import json, time, uuid
from pathlib import Path
import lldb
import trace_callback

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

def run(debugger,plan_name):
    plan=json.loads(Path(plan_name).read_text(encoding='utf-8'))
    result_path=Path(plan['resultPath']); trace_path=Path(plan['tracePath'])
    result={'status':'FAIL','scope':'observational LLDB attach; no expressions/private calls/memory writes',
            'SYNC-001':'NOT RUN','pid':plan.get('pid'),'breakpoints':[],'detached':False}
    target=None; process=None; attached=False
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
        module_map={}
        module_names={}
        for item in plan['modules']:
            module=_module_by_path(target,item['path'])
            if module is None or not module.IsValid():
                raise RuntimeError('Required module is not loaded: '+item['key'])
            actual_uuid=str(uuid.UUID(module.GetUUIDString())).lower()
            expected=str(uuid.UUID(item['uuid'])).lower()
            if actual_uuid!=expected:
                raise RuntimeError('Loaded module UUID mismatch: '+item['key'])
            module_map[actual_uuid]=item['sha256']
            module_names[item['key']]=Path(item['path']).name
        for item in plan['breakpoints']:
            bp=target.BreakpointCreateByRegex(item['regex'],module_names[item['module']])
            count=bp.GetNumLocations()
            row={'id':bp.GetID(),'label':item['label'],'module':item['module'],
                 'regex':item['regex'],'locations':count}
            result['breakpoints'].append(row)
            if count<int(item['minLocations']) or count>int(item['maxLocations']):
                raise RuntimeError('Breakpoint location count outside declared bounds: '+item['label'])
            if not bp.SetScriptCallbackFunction('trace_callback.on_breakpoint'):
                raise RuntimeError('Could not bind trace callback: '+item['label'])
        trace_callback.start_capture(trace_path,plan['runId'],int(plan['pid']),module_map,
                                     max_events=int(plan.get('maxEvents',5000)),
                                     max_seconds=int(plan['durationSeconds'])+30)
        trace_callback.mark_phase('attach-verified')
        debugger.SetAsync(True)
        cont=process.Continue()
        if cont.Fail():
            raise RuntimeError('Could not continue attached process: '+str(cont))
        started=time.monotonic()
        for phase in plan['phases']:
            target_time=started+float(phase['offsetSeconds'])
            while time.monotonic()<target_time:
                time.sleep(min(0.25,target_time-time.monotonic()))
            trace_callback.mark_phase(phase['label'])
            print('FSTR PHASE: '+phase['label']+' — '+phase['instruction'],flush=True)
        end=started+float(plan['durationSeconds'])
        while time.monotonic()<end:
            time.sleep(min(0.25,end-time.monotonic()))
        debugger.SetAsync(False)
        stop_error=process.Stop()
        if stop_error.Fail():
            raise RuntimeError('Could not pause process for clean detach: '+str(stop_error))
        trace_callback.mark_phase('capture-finished')
        trace_callback.stop_capture()
        detach_error=process.Detach()
        if detach_error.Fail():
            raise RuntimeError('Detach failed: '+str(detach_error))
        attached=False
        result.update(status='PASS',stage='complete',detached=True,
                      note='PASS means observer ran and detached, not notification coverage.')
        _write(result_path,result)
    except Exception as error:
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
                result['detached']=not detach_error.Fail()
                attached=False
            except Exception as detach_problem:
                result['detachError']=str(detach_problem)
        try: _write(result_path,result)
        except FileExistsError: pass
    finally:
        trace_callback.stop_capture()
        if target and target.IsValid():
            debugger.DeleteTarget(target)
