#!/usr/bin/env python3
"""Automated no-LLDB script-origin runtime smoke for the FSTR chain probe.

Safety: exact AE 25.6.0.101 only; refuses an already-running AE; uses only a
fresh empty unsaved project; installs only the identified per-user research
bundle; never changes preferences/security; never force-kills AE.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import plistlib
import shutil
import subprocess
import sys
import time
import uuid
from fractions import Fraction
from pathlib import Path

SOURCE=Path(__file__).resolve().parent
ROOT=Path(__file__).resolve().parents[3]

def load_module(name,filename):
    spec=importlib.util.spec_from_file_location(name,SOURCE/filename)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

base=load_module('fstr_chain_disabled_start','run_disabled_start.py')
trace_gate=load_module('fstr_chain_trace_acceptance','trace_acceptance.py')

class GateError(RuntimeError):
    pass

def applescript_quote(value):
    return '"' + str(value).replace('\\','\\\\').replace('"','\\"').replace('\r','\\r').replace('\n','\\n') + '"'

def do_script(app_name,script,timeout=30):
    apple=(
        'tell application '+applescript_quote(app_name)+'\n'
        'set fstrResult to DoScript '+applescript_quote(script)+'\n'
        'return fstrResult\n'
        'end tell'
    )
    done=base.run(['/usr/bin/osascript','-e',apple],timeout=timeout)
    return done.stdout.strip()

def build_active(sdk):
    done=base.run(
        [sys.executable,'-B',str(base.BUILD_SCRIPT),'--sdk',str(Path(sdk).expanduser()),'--research-opt-in'],
        timeout=180,
    )
    try:
        record=json.loads(done.stdout.strip().splitlines()[-1])
    except (IndexError,json.JSONDecodeError) as error:
        raise GateError('BUILD_RECORD_OUTPUT_INVALID') from error
    if record.get('privateProbeOptIn') is not True or record.get('handoffApproved') is not False:
        raise GateError('BUILD_MODE_NOT_RESEARCH_OPT_IN')
    commit=record.get('sourceCommit')
    if not isinstance(commit,str) or len(commit)!=40:
        raise GateError('BUILD_SOURCE_ID_INVALID')
    out=ROOT/'dist/chain-probe'/(commit+'-research-opt-in')
    bundle=out/'FSTRChainProbe.plugin'; record_path=out/'build-record.json'
    if not bundle.is_dir() or not record_path.is_file():
        raise GateError('BUILD_OUTPUT_MISSING')
    disk=json.loads(record_path.read_text(encoding='utf-8'))
    if disk!=record:
        raise GateError('BUILD_RECORD_MISMATCH')
    return bundle,record,record_path

def verify_active_bundle(bundle,record):
    bundle=Path(bundle)
    expected=record.get('files')
    if not isinstance(expected,dict) or not expected:
        raise GateError('BUILD_FILE_MAP_INVALID')
    actual={}
    for path in sorted(bundle.rglob('*')):
        if path.is_symlink():
            raise GateError('BUNDLE_SYMLINK_REFUSED')
        if path.is_file():
            actual[str(path.relative_to(bundle))]=base.digest(path)
    if actual!=expected:
        raise GateError('BUNDLE_FILE_MAP_MISMATCH')
    receipt=base.read_receipt(bundle)
    if receipt.get('sourceCommit')!=record.get('sourceCommit') or receipt.get('buildId')!=record.get('buildId'):
        raise GateError('BUNDLE_RECEIPT_IDENTITY_MISMATCH')
    if receipt.get('privateProbeOptIn') is not True:
        raise GateError('BUNDLE_RECEIPT_MODE_MISMATCH')
    return actual

def install_active(bundle,record):
    base.OWNED_ROOT.mkdir(parents=True,exist_ok=True)
    try:
        shutil.copytree(bundle,base.TARGET)
        verify_active_bundle(base.TARGET,record)
        base.run(['/usr/bin/codesign','--verify','--strict',str(base.TARGET)],timeout=30)
        return base.TARGET
    except Exception:
        if base.TARGET.is_symlink():
            base.TARGET.unlink()
        elif base.TARGET.exists():
            shutil.rmtree(base.TARGET)
        try: base.OWNED_ROOT.rmdir()
        except OSError: pass
        raise

def read_events(path,build_id):
    rows=[]
    try:
        raw=Path(path).read_text(encoding='utf-8')
    except (OSError,UnicodeError):
        return rows
    for line in raw.splitlines():
        try: row=json.loads(line)
        except json.JSONDecodeError: continue
        if row.get('buildId')==build_id and isinstance(row.get('event'),str):
            rows.append(row)
    return rows

def wait_for_prefix(path,build_id,prefix,deadline):
    while time.monotonic()<deadline:
        rows=read_events(path,build_id)
        if any(row['event'].startswith(prefix) for row in rows):
            return rows
        time.sleep(0.2)
    raise GateError('TRACE_EVENT_TIMEOUT:'+prefix)

def observation_count(path,build_id):
    return sum(1 for row in read_events(path,build_id)
               if row['event'].startswith('OBSERVATION_NOT_COMMIT_PROOF'))

def wait_for_new_observation(path,build_id,before,deadline,label):
    while time.monotonic()<deadline:
        count=observation_count(path,build_id)
        if count>before:
            return count
        time.sleep(0.2)
    raise GateError('OBSERVATION_TIMEOUT:'+label)

def require_empty_unsaved_project(app_name):
    script=(
        'if(!app.project) throw new Error("FSTR_NO_PROJECT");'
        'if(app.project.file!==null||app.project.numItems!==0) throw new Error("FSTR_NONEMPTY_PROJECT");'
        '"EMPTY_UNSAVED";'
    )
    try:
        result=do_script(app_name,script)
    except Exception as error:
        raise GateError('BLOCKED_PROJECT_NOT_PROVEN_EMPTY:'+str(error)) from error
    if 'EMPTY_UNSAVED' not in result:
        raise GateError('BLOCKED_PROJECT_NOT_PROVEN_EMPTY')

def create_owned_test_project(app_name):
    script=(
        'var c=app.project.items.addComp("FSTR Chain Probe Test",640,360,1,10,24);'
        'var l=c.layers.addShape();'
        'l.name="FSTR Probe Layer";'
        'l.startTime=0; l.inPoint=0; l.outPoint=10;'
        'c.openInViewer(); l.selected=true;'
        '"FSTR_OWNED_PROJECT_CREATED:"+l.id.toString();'
    )
    result=do_script(app_name,script)
    marker='FSTR_OWNED_PROJECT_CREATED:'
    if marker not in result:
        raise GateError('TEST_PROJECT_CREATE_UNCONFIRMED')
    value=result.split(marker,1)[1].strip()
    try: layer_id=int(value)
    except ValueError as error: raise GateError('TEST_LAYER_ID_INVALID') from error
    if layer_id<=0: raise GateError('TEST_LAYER_ID_INVALID')
    return layer_id

def require_owned_project_and_close(app_name):
    script=(
        'if(!app.project||app.project.file!==null||app.project.numItems!==1) throw new Error("FSTR_NOT_OWNED");'
        'var c=app.project.item(1);'
        'if(!(c instanceof CompItem)||c.name!=="FSTR Chain Probe Test"||c.numLayers!==1||'
        'c.layer(1).name!=="FSTR Probe Layer") throw new Error("FSTR_NOT_OWNED");'
        'app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);'
        '"FSTR_OWNED_PROJECT_CLOSED";'
    )
    result=do_script(app_name,script)
    if 'FSTR_OWNED_PROJECT_CLOSED' not in result:
        raise GateError('OWNED_PROJECT_CLOSE_UNCONFIRMED')

def toggle_probe(app_name):
    script=(
        'var id=app.findMenuCommandId("FSTR Chain Probe: Start / Stop (research)");'
        'if(!id) throw new Error("FSTR_COMMAND_NOT_FOUND");'
        'app.executeCommand(id);'
        '"FSTR_TOGGLE:"+id.toString();'
    )
    result=do_script(app_name,script)
    if 'FSTR_TOGGLE:' not in result:
        raise GateError('PROBE_TOGGLE_UNCONFIRMED')
    return result

def fraction_pair(value):
    try:
        fraction=Fraction(str(value))
    except (ValueError,ZeroDivisionError) as error:
        raise GateError('LAYER_STATE_TIME_INVALID') from error
    return [fraction.numerator,fraction.denominator]

def read_layer_state(app_name,label):
    script=(
        'var c=app.project.activeItem;'
        'if(!(c instanceof CompItem)||c.name!=="FSTR Chain Probe Test") throw new Error("FSTR_COMP_MISMATCH");'
        'var l=c.layer(1); if(l.name!=="FSTR Probe Layer") throw new Error("FSTR_LAYER_MISMATCH");'
        '"FSTR_LAYER_STATE:"+[l.id,l.startTime,l.inPoint,(l.outPoint-l.inPoint)].join("|");'
    )
    result=do_script(app_name,script)
    marker='FSTR_LAYER_STATE:'
    if marker not in result:
        raise GateError('LAYER_STATE_UNCONFIRMED')
    fields=result.split(marker,1)[1].strip().split('|')
    if len(fields)!=4:
        raise GateError('LAYER_STATE_FORMAT_INVALID')
    try:
        layer_id=int(fields[0])
    except ValueError as error:
        raise GateError('LAYER_STATE_ID_INVALID') from error
    if layer_id<=0:
        raise GateError('LAYER_STATE_ID_INVALID')
    state={'label':label,'id':layer_id,'offset':fraction_pair(fields[1]),
           'in':fraction_pair(fields[2]),'duration':fraction_pair(fields[3])}
    if state['duration'][0]<0:
        raise GateError('LAYER_STATE_DURATION_INVALID')
    return state

def set_start_time(app_name,value):
    script=(
        'var c=app.project.activeItem;'
        'if(!(c instanceof CompItem)||c.name!=="FSTR Chain Probe Test") throw new Error("FSTR_COMP_MISMATCH");'
        'var l=c.layer(1); if(l.name!=="FSTR Probe Layer") throw new Error("FSTR_LAYER_MISMATCH");'
        'l.startTime='+str(float(value))+';'
        '"FSTR_START_TIME:"+l.startTime.toString();'
    )
    result=do_script(app_name,script)
    if 'FSTR_START_TIME:' not in result:
        raise GateError('SCRIPT_EDIT_UNCONFIRMED')
    return result

def execute_named_command(app_name,name):
    script=(
        'var id=app.findMenuCommandId('+json.dumps(name)+');'
        'if(!id) throw new Error("FSTR_MENU_COMMAND_NOT_FOUND");'
        'app.executeCommand(id);'
        '"FSTR_COMMAND:'+name+'";'
    )
    result=do_script(app_name,script)
    if 'FSTR_COMMAND:'+name not in result:
        raise GateError('SCRIPT_COMMAND_UNCONFIRMED:'+name)

def write_evidence(run_id,payload):
    out=ROOT/'dist/chain-probe-runtime'/run_id
    out.mkdir(parents=True,exist_ok=True)
    path=out/'script-origin.json'
    path.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk',type=Path,required=True)
    parser.add_argument('--ae-app',type=Path)
    parser.add_argument('--timeout',type=int,default=60)
    args=parser.parse_args()

    run_id='script-origin-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+uuid.uuid4().hex[:10]
    evidence={'schemaVersion':1,'kind':'FSTRChainProbeScriptOrigin','runId':run_id,
              'status':'FAIL','AEGP_load':'NOT RUN','SYNC-001':'NOT RUN','handoffApproved':False}
    trace_path=None; installed=False; safe_empty=False; owned_project=False
    try:
        if base.platform.system()!='Darwin' or base.platform.machine()!='arm64':
            raise GateError('BLOCKED_NATIVE_APPLE_SILICON_REQUIRED')
        if base.ae_pids():
            raise GateError('BLOCKED_AE_ALREADY_RUNNING')
        app=base.discover_ae_app(args.ae_app)
        evidence['aeApp']=str(app['path']); evidence['aeVersion']=base.AE_BUILD_VERSION
        base.clean_owned_install(); base.refuse_conflicting_copies(app['path'])
        bundle,record,record_path=build_active(args.sdk)
        verify_active_bundle(bundle,record)
        evidence['sourceCommit']=record['sourceCommit']; evidence['buildId']=record['buildId']
        evidence['buildRecordSha256']=base.digest(record_path)
        install_active(bundle,record); installed=True
        before=set(Path('/tmp').glob('FSTRChainProbe-*-'+record['buildId']+'-*'))
        base.launch_ae(app); base.wait_for_ae(time.monotonic()+args.timeout,True)
        trace_path=base.new_trace(record['buildId'],before,time.monotonic()+args.timeout)
        base.trace_ready(trace_path,record['buildId'],time.monotonic()+args.timeout)
        require_empty_unsaved_project(app['name']); safe_empty=True
        layer_id=create_owned_test_project(app['name']); owned_project=True
        evidence['testLayerId']=layer_id
        toggle_probe(app['name'])
        wait_for_prefix(trace_path,record['buildId'],'REGISTERED_RESEARCH_ONLY_SYNC001_NOT_RUN',
                        time.monotonic()+args.timeout)

        phases=[]; expected_states=[]
        for label,action in (
            ('script-edit-1',lambda:set_start_time(app['name'],1.0)),
            ('script-edit-2',lambda:set_start_time(app['name'],2.0)),
            ('undo',lambda:execute_named_command(app['name'],'Undo')),
            ('redo',lambda:execute_named_command(app['name'],'Redo')),
        ):
            before_count=observation_count(trace_path,record['buildId'])
            started=time.time_ns(); action(); ended=time.time_ns()
            state=read_layer_state(app['name'],label)
            if state['id']!=layer_id:
                raise GateError('LAYER_STATE_ID_CHANGED:'+label)
            expected_states.append(state)
            after_count=wait_for_new_observation(
                trace_path,record['buildId'],before_count,time.monotonic()+args.timeout,label)
            phases.append({'label':label,'startedNs':started,'endedNs':ended,
                           'observationsBefore':before_count,'observationsAfter':after_count,
                           'publicState':state})

        toggle_probe(app['name'])
        wait_for_prefix(trace_path,record['buildId'],'REMOVED_OWN_ID',time.monotonic()+args.timeout)
        require_owned_project_and_close(app['name']); owned_project=False
        base.request_quit(app['name']); base.wait_for_ae(time.monotonic()+args.timeout,False)

        rows=trace_gate.parse_trace(trace_path,record['buildId'])
        result=trace_gate.verify_expected_states(rows,expected_states)
        evidence.update({'status':'PASS','AEGP_load':'OBSERVED',
                         'SYNC-001':'PARTIAL_SCRIPT_ORIGIN_RUNTIME_EVIDENCE_ONLY',
                         'traceResult':result,'phases':phases,'expectedStates':expected_states,
                         'traceSha256':base.digest(trace_path)})
        out=ROOT/'dist/chain-probe-runtime'/run_id; out.mkdir(parents=True,exist_ok=True)
        shutil.copy2(trace_path,out/'trace.jsonl')
    except (OSError,subprocess.SubprocessError,GateError,base.GateError,
            plistlib.InvalidFileException,trace_gate.EvidenceError) as error:
        evidence['error']=str(error)
        if str(error).startswith('BLOCKED_'):
            evidence['status']='BLOCKED'
        raise
    finally:
        ae_running=base.cleanup_ae_running(evidence)
        if owned_project and ae_running is True:
            try:
                require_owned_project_and_close(app['name'])
                owned_project=False; evidence['ownedProjectCleanup']='PASS'
                safe_empty=True
            except Exception as cleanup_error:
                evidence['ownedProjectCleanup']='FAIL:'+str(cleanup_error)
        elif owned_project and ae_running is False:
            evidence['ownedProjectCleanup']='AE_ALREADY_EXITED'
        elif owned_project:
            evidence['ownedProjectCleanup']='DEFERRED_AE_STATE_UNKNOWN'
        elif safe_empty:
            evidence['ownedProjectCleanup']='NOT_NEEDED_OR_ALREADY_CLOSED'
        else:
            evidence['ownedProjectCleanup']='NOT_SAFE_TO_TOUCH'

        if safe_empty and not owned_project and ae_running is True:
            try:
                base.request_quit(app['name'])
                base.wait_for_ae(time.monotonic()+args.timeout,False)
                evidence['aeQuitCleanup']='PASS'
                ae_running=False
            except Exception as cleanup_error:
                evidence['aeQuitCleanup']='FAIL:'+str(cleanup_error)
                ae_running=base.cleanup_ae_running(evidence)
        else:
            evidence['aeQuitCleanup']='NOT_SAFE_OR_NOT_NEEDED'

        if installed and ae_running is False:
            try:
                base.clean_owned_install(); evidence['ownedInstallCleanup']='PASS'
            except Exception as cleanup_error:
                evidence['ownedInstallCleanup']='FAIL:'+str(cleanup_error)
        elif installed and ae_running is True:
            evidence['ownedInstallCleanup']='DEFERRED_AE_RUNNING'
        elif installed:
            evidence['ownedInstallCleanup']='DEFERRED_AE_STATE_UNKNOWN'
        else:
            evidence['ownedInstallCleanup']='NOT_NEEDED'

        evidence_path=write_evidence(run_id,evidence)
        print(json.dumps({'evidence':str(evidence_path),'status':evidence['status']}))
        if trace_path and trace_path.exists() and ae_running is False:
            try: trace_path.unlink()
            except OSError: pass

if __name__=='__main__':
    try:
        main()
    except Exception as error:
        raise SystemExit(str(error))
