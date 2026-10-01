#!/usr/bin/env python3
"""Run the two no-LLDB native AE gates in safe order and aggregate evidence.

The disabled-start gate must PASS before the research-opt-in script-origin gate
is allowed to run. Child runners own their bounded timeouts and cleanup.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
SOURCE=Path(__file__).resolve().parent
EVIDENCE_ROOT=ROOT/'dist/chain-probe-runtime'
STAGES=(
    ('disabled','run_disabled_start.py','FSTRChainProbeDisabledStart'),
    ('script-origin','run_script_origin.py','FSTRChainProbeScriptOrigin'),
)

class GateError(RuntimeError):
    pass

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()

def _result_envelope(stdout):
    for line in reversed(stdout.splitlines()):
        try:
            row=json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row,dict) and set(row)=={'evidence','status'}:
            return row
    raise GateError('CHILD_RESULT_ENVELOPE_MISSING')

def _inside(path,root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False

def read_child_evidence(path,expected_kind,expected_status,evidence_root=EVIDENCE_ROOT):
    raw=Path(path)
    if raw.is_symlink():
        raise GateError('CHILD_EVIDENCE_SYMLINK_REFUSED')
    path=raw.resolve(strict=True)
    root=Path(evidence_root).resolve(strict=True)
    if not _inside(path,root) or not path.is_file():
        raise GateError('CHILD_EVIDENCE_PATH_REFUSED')
    size=path.stat().st_size
    if size<=0 or size>256*1024:
        raise GateError('CHILD_EVIDENCE_SIZE_INVALID')
    try:
        row=json.loads(path.read_text(encoding='utf-8',errors='strict'))
    except (UnicodeError,json.JSONDecodeError) as error:
        raise GateError('CHILD_EVIDENCE_JSON_INVALID') from error
    if (not isinstance(row,dict) or row.get('schemaVersion')!=1 or
        row.get('kind')!=expected_kind or row.get('handoffApproved') is not False or
        row.get('status')!=expected_status):
        raise GateError('CHILD_EVIDENCE_IDENTITY_INVALID')
    root_identity=Path(ROOT).resolve(strict=True)
    if not _inside(path,root_identity):
        raise GateError('CHILD_EVIDENCE_REPO_PATH_REFUSED')
    summary={
        'kind':expected_kind,
        'status':row['status'],
        'evidence':str(path.relative_to(root_identity)),
        'sha256':digest(path),
        'AEGP_load':row.get('AEGP_load','NOT RUN'),
        'SYNC-001':row.get('SYNC-001','NOT RUN'),
    }
    if row['status']=='PASS':
        commit=row.get('sourceCommit'); build_id=row.get('buildId')
        if (not isinstance(commit,str) or not re.fullmatch(r'[0-9a-f]{40}',commit) or
            not isinstance(build_id,str) or not build_id):
            raise GateError('CHILD_PASS_BUILD_IDENTITY_MISSING')
        summary.update({'sourceCommit':commit,'buildId':build_id,'aeVersion':row.get('aeVersion')})
    return summary

def run_stage(stage,sdk,ae_app,timeout):
    match=[row for row in STAGES if row[0]==stage]
    if len(match)!=1:
        raise GateError('UNKNOWN_STAGE:'+stage)
    _,script_name,kind=match[0]
    args=[sys.executable,'-B',str(SOURCE/script_name),'--sdk',str(Path(sdk).expanduser()),
          '--timeout',str(timeout)]
    if ae_app is not None:
        args += ['--ae-app',str(Path(ae_app).expanduser())]
    # Do not add a parent timeout: each child owns bounded commands and safety
    # cleanup. Killing the child here could strand a loaded helper or AE process.
    done=subprocess.run(args,capture_output=True,text=True)
    envelope=_result_envelope(done.stdout)
    status=envelope['status']
    if status not in ('PASS','FAIL','BLOCKED'):
        raise GateError('CHILD_STATUS_INVALID')
    summary=read_child_evidence(envelope['evidence'],kind,status)
    if (done.returncode==0)!=(status=='PASS'):
        raise GateError('CHILD_EXIT_STATUS_MISMATCH:'+stage)
    return summary

def orchestrate(sdk,ae_app=None,timeout=60,runner=run_stage):
    result={
        'schemaVersion':1,
        'kind':'FSTRChainProbeNativeGates',
        'status':'FAIL',
        'AEGP_load':'NOT RUN',
        'SYNC-001':'NOT RUN',
        'handoffApproved':False,
        'stages':[],
    }
    disabled=runner('disabled',sdk,ae_app,timeout)
    result['stages'].append(disabled)
    if disabled['status']!='PASS':
        result['status']=disabled['status']
        result['stoppedAfter']='disabled'
        return result
    active=runner('script-origin',sdk,ae_app,timeout)
    result['stages'].append(active)
    if active['status']!='PASS':
        result['status']=active['status']
        result['stoppedAfter']='script-origin'
        return result
    if disabled.get('sourceCommit')!=active.get('sourceCommit'):
        raise GateError('CHILD_SOURCE_COMMIT_MISMATCH')
    if disabled.get('aeVersion')!=active.get('aeVersion'):
        raise GateError('CHILD_AE_VERSION_MISMATCH')
    result.update({
        'status':'PASS',
        'sourceCommit':active['sourceCommit'],
        'aeVersion':active.get('aeVersion'),
        'AEGP_load':'OBSERVED',
        'SYNC-001':'PARTIAL_SCRIPT_ORIGIN_RUNTIME_EVIDENCE_ONLY',
        'stoppedAfter':None,
    })
    return result

def write_evidence(payload):
    run_id='native-gates-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+uuid.uuid4().hex[:10]
    out=EVIDENCE_ROOT/run_id
    out.mkdir(parents=True,exist_ok=False)
    path=out/'native-gates.json'
    path.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk',type=Path,required=True)
    parser.add_argument('--ae-app',type=Path)
    parser.add_argument('--timeout',type=int,default=60)
    args=parser.parse_args()
    payload={
        'schemaVersion':1,'kind':'FSTRChainProbeNativeGates','status':'FAIL',
        'AEGP_load':'NOT RUN','SYNC-001':'NOT RUN','handoffApproved':False,'stages':[],
    }
    try:
        if args.timeout<10 or args.timeout>600:
            raise GateError('TIMEOUT_RANGE_INVALID')
        payload=orchestrate(args.sdk,args.ae_app,args.timeout)
    except (OSError,subprocess.SubprocessError,GateError) as error:
        payload['error']=str(error)
        if str(error).startswith('BLOCKED_'):
            payload['status']='BLOCKED'
    path=write_evidence(payload)
    print(json.dumps({'evidence':str(path),'status':payload['status']}))
    return 0 if payload['status']=='PASS' else 1

if __name__=='__main__':
    raise SystemExit(main())
