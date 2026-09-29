"""Opt-in LLDB callback logger. Does not attach, create breakpoints or evaluate target code."""
from __future__ import annotations
import json, os, re, threading, time, uuid
from pathlib import Path

_lock=threading.RLock()
_capture=None

def _safe_uuid(value):
    try:
        return str(uuid.UUID(value)).lower()
    except Exception:
        return None

def start_capture(path,run_id,expected_pid,modules,breakpoints=None,max_events=5000,max_seconds=180,max_frames=8):
    """Start a bounded observer capture tied to exact PID/module identities."""
    global _capture
    if not isinstance(run_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',run_id):
        raise ValueError('Invalid run ID')
    if not isinstance(expected_pid,int) or expected_pid<=0:
        raise ValueError('An explicit test-process PID is required')
    if not 1<=max_events<=10000 or not 1<=max_seconds<=600 or not 0<=max_frames<=16:
        raise ValueError('Capture bounds exceeded')
    if not modules or len(modules)>64:
        raise ValueError('Exact identified modules are required')
    normalized={}
    for module_uuid,digest in modules.items():
        if not re.fullmatch(r'[a-f0-9]{64}',digest):
            raise ValueError('Invalid module digest')
        normalized[str(uuid.UUID(module_uuid)).lower()]=digest
    bp_meta={}
    for key,value in (breakpoints or {}).items():
        bp_id=int(key)
        if bp_id<=0 or not isinstance(value,dict):
            raise ValueError('Invalid breakpoint metadata')
        label=value.get('label','')
        role=value.get('role','candidate')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',label) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',role):
            raise ValueError('Invalid breakpoint label/role')
        bp_meta[bp_id]={'label':label,'role':role}
    with _lock:
        if _capture is not None:
            raise RuntimeError('A capture is already active')
        fd=os.open(Path(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        stream=os.fdopen(fd,'w',encoding='utf-8')
        _capture={'stream':stream,'runId':run_id,'pid':expected_pid,'modules':normalized,
                  'breakpoints':bp_meta,'maxFrames':max_frames,
                  'started':time.monotonic_ns(),'sequence':0,'hits':0,
                  'maxEvents':max_events,'maxNs':int(max_seconds*1e9),'stopped':False}
        _write({'kind':'capture-start','moduleIdentities':normalized,
                'breakpointMetadata':bp_meta,
                'moduleHashesIndependentlyVerifiedByLogger':False})

def _write(fields):
    _capture['sequence']+=1
    row=dict(fields,testRunId=_capture['runId'],sequence=_capture['sequence'],
             monotonicNs=time.monotonic_ns(),wallTimeNs=time.time_ns())
    _capture['stream'].write(json.dumps(row,ensure_ascii=True)+'\n')
    _capture['stream'].flush()

def mark_phase(label):
    with _lock:
        if _capture is None or _capture['stopped']:
            raise RuntimeError('No active capture')
        if not isinstance(label,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',label):
            raise ValueError('Invalid phase label')
        _write({'kind':'phase','label':label})

def _frame_row(frame):
    try:
        address=frame.GetPCAddress()
        module=address.GetModule()
        module_name=None
        try:
            spec=module.GetFileSpec()
            module_name=spec.GetFilename() if spec and spec.IsValid() else None
        except Exception:
            pass
        return {'function':frame.GetFunctionName(),
                'moduleUUID':_safe_uuid(module.GetUUIDString()),
                'moduleName':module_name,
                'unslidAddress':hex(address.GetFileAddress())}
    except Exception:
        return {'function':None,'moduleUUID':None,'moduleName':None,'unslidAddress':None}

def _stack(thread):
    rows=[]
    try:
        count=min(int(thread.GetNumFrames()),_capture['maxFrames'])
        for index in range(count):
            row=_frame_row(thread.GetFrameAtIndex(index))
            row['index']=index
            rows.append(row)
    except Exception:
        pass
    return rows

def on_breakpoint(frame,bp_loc,internal_dict):
    """False resumes after this breakpoint; True pauses. Never calls EvaluateExpression."""
    with _lock:
        if _capture is None or _capture['stopped']:
            return True
        try:
            if (_capture['hits']>=_capture['maxEvents'] or
                    time.monotonic_ns()-_capture['started']>=_capture['maxNs']):
                _capture['stopped']=True
                _write({'kind':'capture-limit','pauseRequested':True})
                return True
            thread=frame.GetThread(); process=thread.GetProcess()
            if process.GetProcessID()!=_capture['pid']:
                raise ValueError('Unexpected process PID')
            address=frame.GetPCAddress()
            module_uuid=str(uuid.UUID(address.GetModule().GetUUIDString())).lower()
            if module_uuid not in _capture['modules']:
                raise ValueError('Unidentified module UUID')
            bp_id=bp_loc.GetBreakpoint().GetID()
            meta=_capture['breakpoints'].get(bp_id,{'label':'unlabeled','role':'candidate'})
            _capture['hits']+=1
            _write({'kind':'candidate-hit','source':'lldb-breakpoint','commitPhase':'UNKNOWN',
                    'pid':_capture['pid'],'threadId':thread.GetThreadID(),
                    'breakpointId':bp_id,'locationId':bp_loc.GetID(),
                    'label':meta['label'],'role':meta['role'],
                    'moduleUUID':module_uuid,'unslidAddress':hex(address.GetFileAddress()),
                    'function':frame.GetFunctionName(),'stack':_stack(thread),
                    'isNotificationProven':False})
            return False
        except Exception as error:
            _capture['stopped']=True
            try:
                _write({'kind':'capture-error','error':str(error),'pauseRequested':True})
            except Exception:
                pass
            return True

def stop_capture():
    global _capture
    with _lock:
        if _capture is not None:
            try:
                _write({'kind':'capture-end','hits':_capture['hits'],'SYNC-001':'NOT RUN'})
            finally:
                _capture['stream'].close()
                _capture=None
