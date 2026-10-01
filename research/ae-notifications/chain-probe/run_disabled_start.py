#!/usr/bin/env python3
"""Build and verify the default-disabled chain probe in exact AE 25.6.0.101.

This is an isolated research gate: no project mutation, no private registration,
no LLDB, no preference/security changes and no system-wide plug-in install.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import platform
import plistlib
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
SOURCE=Path(__file__).resolve().parent
BUILD_SCRIPT=SOURCE/'build_probe.py'
USER_MEDIA=Path.home()/'Library/Application Support/Adobe/Common/Plug-ins/7.0/MediaCore'
OWNED_ROOT=USER_MEDIA/'FSTR-Line-Research'
TARGET=OWNED_ROOT/'FSTRChainProbe.plugin'
BUNDLE_ID='tv.fstr.line.chain-probe'
AE_BUNDLE_ID='com.adobe.AfterEffects.application'
AE_SHORT_VERSION='25.6.0'
AE_BUILD_VERSION='25.6.0.101'
AE_PROCESS_PATTERN=r'Adobe After Effects.*\\.app/Contents/MacOS/After Effects'

class GateError(RuntimeError):
    pass

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()

def run(args,timeout=120,check=True):
    done=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
    if check and done.returncode:
        detail=(done.stderr or done.stdout).strip()
        raise GateError(f'COMMAND_FAILED:{Path(args[0]).name}:{done.returncode}:{detail[:400]}')
    return done

def read_plist(bundle):
    path=Path(bundle)/'Contents/Info.plist'
    if path.is_symlink() or not path.is_file():
        raise GateError('BUNDLE_INFO_MISSING')
    with path.open('rb') as handle:
        return plistlib.load(handle)

def validate_ae_app(path):
    path=Path(path).expanduser().resolve(strict=True)
    if path.suffix!='.app' or not path.is_dir():
        raise GateError('AE_APP_INVALID')
    info=read_plist(path)
    if (info.get('CFBundleIdentifier')!=AE_BUNDLE_ID or
        info.get('CFBundleShortVersionString')!=AE_SHORT_VERSION or
        info.get('CFBundleVersion')!=AE_BUILD_VERSION):
        raise GateError('AE_APP_IDENTITY_MISMATCH')
    name=info.get('CFBundleName')
    executable=info.get('CFBundleExecutable')
    if not isinstance(name,str) or not name or not isinstance(executable,str) or not executable:
        raise GateError('AE_APP_METADATA_INVALID')
    exe=path/'Contents/MacOS'/executable
    if not exe.is_file():
        raise GateError('AE_EXECUTABLE_MISSING')
    return {'path':path,'name':name,'executable':exe}

def discover_ae_app(explicit=None):
    if explicit:
        return validate_ae_app(explicit)
    candidates=[]
    root=Path('/Applications')
    if root.is_dir():
        for parent in root.glob('Adobe After Effects*'):
            if not parent.is_dir():
                continue
            for app in parent.glob('*.app'):
                try:
                    candidates.append(validate_ae_app(app))
                except (OSError,GateError,plistlib.InvalidFileException):
                    pass
    if len(candidates)!=1:
        raise GateError('AE_EXACT_APP_NOT_UNIQUE')
    return candidates[0]

def ae_pids():
    if platform.system()!='Darwin':
        return []
    done=run(['/usr/bin/pgrep','-f',AE_PROCESS_PATTERN],timeout=5,check=False)
    if done.returncode not in (0,1):
        raise GateError('AE_PROCESS_QUERY_FAILED')
    return [int(value) for value in done.stdout.split() if value.isdigit()]

def read_receipt(bundle):
    path=Path(bundle)/'Contents/Resources/FSTRChainProbeBuild.json'
    if path.is_symlink() or not path.is_file():
        raise GateError('OWNERSHIP_RECEIPT_MISSING')
    try:
        row=json.loads(path.read_text(encoding='utf-8'))
    except (UnicodeError,json.JSONDecodeError) as error:
        raise GateError('OWNERSHIP_RECEIPT_INVALID') from error
    if (not isinstance(row,dict) or row.get('schemaVersion')!=1 or
        row.get('kind')!='FSTRChainProbeResearch' or
        row.get('handoffApproved') is not False):
        raise GateError('OWNERSHIP_RECEIPT_INVALID')
    return row

def is_owned_bundle(bundle):
    try:
        info=read_plist(bundle)
        receipt=read_receipt(bundle)
        return info.get('CFBundleIdentifier')==BUNDLE_ID and isinstance(receipt.get('buildId'),str)
    except (OSError,GateError,plistlib.InvalidFileException):
        return False

def clean_owned_install():
    if not OWNED_ROOT.exists():
        return
    if OWNED_ROOT.is_symlink() or not OWNED_ROOT.is_dir():
        raise GateError('OWNED_ROOT_UNSAFE')
    entries=list(OWNED_ROOT.iterdir())
    if TARGET.is_symlink():
        raise GateError('OWNED_TARGET_SYMLINK_REFUSED')
    if any(entry!=TARGET for entry in entries):
        raise GateError('OWNED_ROOT_UNKNOWN_CONTENT')
    if TARGET.exists() and not is_owned_bundle(TARGET):
        raise GateError('OWNED_TARGET_NOT_IDENTIFIED')
    if TARGET.exists():
        shutil.rmtree(TARGET)
    try:
        OWNED_ROOT.rmdir()
    except OSError:
        pass

def plugin_bundles(root,max_depth=10):
    root=Path(root)
    if not root.is_dir():
        return []
    found=[]
    root_depth=len(root.parts)
    for current,dirs,_ in os.walk(root,followlinks=False):
        current_path=Path(current)
        depth=len(current_path.parts)-root_depth
        if depth>=max_depth:
            dirs[:]=[]
            continue
        keep=[]
        for name in dirs:
            child=current_path/name
            if name.endswith('.plugin'):
                found.append(child)
            elif not child.is_symlink():
                keep.append(name)
        dirs[:]=keep
    return found

def refuse_conflicting_copies(ae_app):
    roots=[
        USER_MEDIA,
        Path('/Library/Application Support/Adobe/Common/Plug-ins/7.0/MediaCore'),
        ae_app/'Plug-ins',
    ]
    conflicts=[]
    target_real=TARGET.resolve(strict=False)
    for root in roots:
        for bundle in plugin_bundles(root):
            try:
                if bundle.resolve(strict=False)==target_real:
                    continue
                if read_plist(bundle).get('CFBundleIdentifier')==BUNDLE_ID:
                    conflicts.append(str(bundle))
            except (OSError,GateError,plistlib.InvalidFileException):
                continue
    if conflicts:
        raise GateError('CONFLICTING_CHAIN_PROBE:'+','.join(sorted(set(conflicts))))

def build_disabled(sdk):
    done=run([sys.executable,'-B',str(BUILD_SCRIPT),'--sdk',str(Path(sdk).expanduser())],timeout=180)
    try:
        record=json.loads(done.stdout.strip().splitlines()[-1])
    except (IndexError,json.JSONDecodeError) as error:
        raise GateError('BUILD_RECORD_OUTPUT_INVALID') from error
    if record.get('privateProbeOptIn') is not False or record.get('handoffApproved') is not False:
        raise GateError('BUILD_MODE_NOT_DISABLED')
    commit=record.get('sourceCommit')
    if not isinstance(commit,str) or not re.fullmatch(r'[0-9a-f]{40}',commit):
        raise GateError('BUILD_SOURCE_ID_INVALID')
    out=ROOT/'dist/chain-probe'/(commit+'-disabled')
    bundle=out/'FSTRChainProbe.plugin'
    record_path=out/'build-record.json'
    if not bundle.is_dir() or not record_path.is_file():
        raise GateError('BUILD_OUTPUT_MISSING')
    disk_record=json.loads(record_path.read_text(encoding='utf-8'))
    if disk_record!=record:
        raise GateError('BUILD_RECORD_MISMATCH')
    return bundle,record,record_path

def verify_bundle_files(bundle,record):
    bundle=Path(bundle)
    expected=record.get('files')
    if not isinstance(expected,dict) or not expected:
        raise GateError('BUILD_FILE_MAP_INVALID')
    actual={}
    for path in sorted(bundle.rglob('*')):
        if path.is_symlink():
            raise GateError('BUNDLE_SYMLINK_REFUSED')
        if path.is_file():
            actual[str(path.relative_to(bundle))]=digest(path)
    if actual!=expected:
        raise GateError('BUNDLE_FILE_MAP_MISMATCH')
    receipt=read_receipt(bundle)
    if receipt.get('sourceCommit')!=record.get('sourceCommit') or receipt.get('buildId')!=record.get('buildId'):
        raise GateError('BUNDLE_RECEIPT_IDENTITY_MISMATCH')
    if receipt.get('privateProbeOptIn') is not False:
        raise GateError('BUNDLE_RECEIPT_MODE_MISMATCH')
    return actual

def install_owned(bundle,record):
    OWNED_ROOT.mkdir(parents=True,exist_ok=True)
    shutil.copytree(bundle,TARGET)
    verify_bundle_files(TARGET,record)
    run(['/usr/bin/codesign','--verify','--strict',str(TARGET)],timeout=30)
    return TARGET

def new_trace(build_id,before,deadline):
    pattern='FSTRChainProbe-*-'+build_id+'-*'
    while time.monotonic()<deadline:
        candidates=[path for path in Path('/tmp').glob(pattern) if path not in before and path.is_file()]
        if len(candidates)==1:
            return candidates[0]
        if len(candidates)>1:
            raise GateError('TRACE_NOT_UNIQUE')
        time.sleep(0.25)
    raise GateError('TRACE_NOT_CREATED')

def trace_ready(path,build_id,deadline):
    while time.monotonic()<deadline:
        try:
            raw=Path(path).read_text(encoding='utf-8')
        except (OSError,UnicodeError):
            time.sleep(0.25); continue
        for line in raw.splitlines():
            try:
                row=json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get('buildId')==build_id and str(row.get('event','')).startswith('COMMAND_READY id='):
                return
        time.sleep(0.25)
    raise GateError('COMMAND_READY_NOT_OBSERVED')

def launch_ae(app):
    done=run(['/usr/bin/open','-n',str(app['path'])],timeout=15)
    return done

def wait_for_ae(deadline,present):
    while time.monotonic()<deadline:
        pids=ae_pids()
        if bool(pids)==present:
            return pids
        time.sleep(0.25)
    raise GateError('AE_PROCESS_STATE_TIMEOUT')

def request_quit(app_name):
    script='const ae=Application('+json.dumps(app_name)+'); ae.quit();'
    run(['/usr/bin/osascript','-l','JavaScript','-e',script],timeout=30)

def load_trace_module():
    import importlib.util
    path=SOURCE/'trace_acceptance.py'
    spec=importlib.util.spec_from_file_location('fstr_chain_trace_acceptance',path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

def write_evidence(run_id,payload):
    out=ROOT/'dist/chain-probe-runtime'/run_id
    out.mkdir(parents=True,exist_ok=True)
    path=out/'disabled-start.json'
    path.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk',type=Path,required=True)
    parser.add_argument('--ae-app',type=Path)
    parser.add_argument('--timeout',type=int,default=60)
    args=parser.parse_args()
    run_id='disabled-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+uuid.uuid4().hex[:10]
    evidence={'schemaVersion':1,'kind':'FSTRChainProbeDisabledStart','runId':run_id,
              'status':'FAIL','AEGP_load':'NOT RUN','SYNC-001':'NOT RUN','handoffApproved':False}
    trace_path=None
    installed_by_run=False
    try:
        if platform.system()!='Darwin' or platform.machine()!='arm64':
            raise GateError('BLOCKED_NATIVE_APPLE_SILICON_REQUIRED')
        if ae_pids():
            raise GateError('BLOCKED_AE_ALREADY_RUNNING')
        app=discover_ae_app(args.ae_app)
        evidence['aeApp']=str(app['path'])
        evidence['aeVersion']=AE_BUILD_VERSION
        clean_owned_install()
        refuse_conflicting_copies(app['path'])
        bundle,record,record_path=build_disabled(args.sdk)
        verify_bundle_files(bundle,record)
        evidence['sourceCommit']=record['sourceCommit']; evidence['buildId']=record['buildId']
        evidence['buildRecordSha256']=digest(record_path)
        install_owned(bundle,record)
        installed_by_run=True
        before=set(Path('/tmp').glob('FSTRChainProbe-*-'+record['buildId']+'-*'))
        launch_ae(app)
        wait_for_ae(time.monotonic()+args.timeout,True)
        trace_path=new_trace(record['buildId'],before,time.monotonic()+args.timeout)
        trace_ready(trace_path,record['buildId'],time.monotonic()+args.timeout)
        request_quit(app['name'])
        wait_for_ae(time.monotonic()+args.timeout,False)
        trace=load_trace_module()
        rows=trace.parse_trace(trace_path,record['buildId'])
        result=trace.verify_disabled(rows)
        evidence.update({'status':'PASS','AEGP_load':'OBSERVED','traceResult':result,
                         'traceSha256':digest(trace_path)})
        out=ROOT/'dist/chain-probe-runtime'/run_id
        out.mkdir(parents=True,exist_ok=True)
        shutil.copy2(trace_path,out/'trace.jsonl')
    except (OSError,subprocess.SubprocessError,GateError,plistlib.InvalidFileException) as error:
        evidence['error']=str(error)
        if str(error).startswith('BLOCKED_'):
            evidence['status']='BLOCKED'
        raise
    finally:
        if installed_by_run:
            try:
                clean_owned_install()
                evidence['ownedInstallCleanup']='PASS'
            except Exception as cleanup_error:
                evidence['ownedInstallCleanup']='FAIL:'+str(cleanup_error)
        else:
            evidence['ownedInstallCleanup']='NOT_NEEDED'
        evidence_path=write_evidence(run_id,evidence)
        print(json.dumps({'evidence':str(evidence_path),'status':evidence['status']}))
        if trace_path and trace_path.exists() and not ae_pids():
            try: trace_path.unlink()
            except OSError: pass

if __name__=='__main__':
    try:
        main()
    except Exception as error:
        raise SystemExit(str(error))
