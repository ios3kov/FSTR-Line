#!/usr/bin/env python3
"""Build/install/observe/uninstall the independent FSTR Plugin Origin diagnostic helper."""
from __future__ import annotations
import argparse, hashlib, json, os, plistlib, re, shlex, shutil, subprocess, sys, tempfile, time, uuid, zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import collect_app
import runtime_protocol

TOOLS=(
    'Build-Install.command','Observe.command','Uninstall.command','plugin_origin_tool.py',
    'plugin_origin_targets.json','PluginOrigin.cpp','PluginOrigin.h','PluginOrigin_PiPL.r',
    'runtime_control.py','trace_callback.py','runtime_protocol.py','collect_app.py','FSTR-Snapshot.jsx'
)

class Blocked(Exception): pass

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def load_manifest():
    manifest=json.loads((ROOT/'build-manifest.json').read_text(encoding='utf-8'))
    if manifest.get('sourceState')!='clean' or set(manifest.get('files',{}))!=set(TOOLS):
        raise ValueError('Invalid Plugin Origin kit manifest')
    for name in TOOLS:
        path=ROOT/name
        if path.is_symlink() or not path.is_file() or sha256(path)!=manifest['files'][name]:
            raise ValueError('Plugin Origin kit hash mismatch: '+name)
    return manifest

def run(args,**kwargs):
    return subprocess.run(args,check=True,**kwargs)

def choose_folder(prompt):
    escaped=prompt.replace('"','\"')
    script=f'try\nset p to choose folder with prompt "{escaped}"\nreturn POSIX path of p\non error number -128\nreturn ""\nend try'
    done=subprocess.run(['/usr/bin/osascript','-e',script],capture_output=True,text=True,timeout=60)
    return Path(done.stdout.strip()).expanduser() if done.returncode==0 and done.stdout.strip() else None

def find_sdk_root(selected):
    selected=Path(selected).expanduser().resolve()
    candidates=[selected]
    for p in selected.glob('**/Examples/Headers/AE_GeneralPlug.h'):
        candidates.append(p.parents[2])
        if len(candidates)>20: break
    for root in candidates:
        if (root/'Examples/Headers/AE_GeneralPlug.h').is_file() and            (root/'Examples/AEGP/Commando/Mac/Commando.xcodeproj').is_dir():
            return root
    raise Blocked('Selected folder does not contain an extracted AE SDK with Examples/Headers and AEGP/Commando')

def shell_quote(value): return shlex.quote(str(value))

def build_install(args):
    manifest=load_manifest()
    if sys.platform!='darwin': raise Blocked('macOS required')
    selected=Path(args.sdk).expanduser() if args.sdk else choose_folder('Select the extracted After Effects 25.6 SDK root (or a parent folder)')
    if not selected: raise Blocked('SDK selection cancelled')
    sdk=find_sdk_root(selected)
    out_root=Path.home()/'Desktop/FSTR-AE-Research'
    out_root.mkdir(parents=True,exist_ok=True)
    build_id='fstr-plugin-origin-'+manifest['sourceCommit'][:12]+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out=out_root/('PluginOriginBuild-'+build_id); out.mkdir(mode=0o700)
    workspace=out/'sdk-workspace'; (workspace/'AEGP').mkdir(parents=True)
    for name in ('Headers','Util','Resources'):
        shutil.copytree(sdk/'Examples'/name,workspace/name)
    shutil.copytree(sdk/'Examples/AEGP/Commando',workspace/'AEGP/Commando')
    probe=workspace/'AEGP/Commando'
    plist=probe/'Mac/Commando.plugin-Info.plist'
    run(['/usr/libexec/PlistBuddy','-c','Set :CFBundleExecutable FSTRPluginOrigin',str(plist)])
    run(['/usr/libexec/PlistBuddy','-c','Set :CFBundleName FSTR Plugin Origin Probe',str(plist)])
    subprocess.run(['/usr/libexec/PlistBuddy','-c','Delete :NSHumanReadableCopyright',str(plist)],
                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    shutil.copyfile(ROOT/'PluginOrigin.cpp',probe/'Commando.cpp')
    shutil.copyfile(ROOT/'PluginOrigin.h',probe/'PluginOrigin.h')
    shutil.copyfile(ROOT/'PluginOrigin_PiPL.r',probe/'Commando_PiPL.r')
    (probe/'PluginOriginBuild.h').write_text(
        '#define FSTR_PLUGIN_ORIGIN_BUILD_ID "'+build_id+'"\n',encoding='utf-8')
    (out/'source-manifest.json').write_text(json.dumps({
        'buildId':build_id,'sourceCommit':manifest['sourceCommit'],
        'sdkRoot':str(sdk),'sdkHeaderSha256':sha256(sdk/'Examples/Headers/AE_GeneralPlug.h'),
        'sourceHashes':{n:manifest['files'][n] for n in ('PluginOrigin.cpp','PluginOrigin.h','PluginOrigin_PiPL.r')}
    },indent=2)+'\n')
    xlog=out/'xcodebuild.log'
    with xlog.open('w') as log:
        done=subprocess.run([
            'xcodebuild','-project',str(probe/'Mac/Commando.xcodeproj'),'-configuration','Debug','-target','Commando',
            'SYMROOT='+str(out/'build'),'OBJROOT='+str(out/'obj'),'build','CODE_SIGNING_ALLOWED=NO',
            'PRODUCT_BUNDLE_IDENTIFIER=com.ios3kov.fstrline.pluginorigin','PRODUCT_NAME=FSTRPluginOrigin',
            'ARCHS=arm64','ONLY_ACTIVE_ARCH=YES','MACOSX_DEPLOYMENT_TARGET=12.0','CLANG_CXX_LANGUAGE_STANDARD=c++17'
        ],stdout=log,stderr=subprocess.STDOUT,text=True)
    if done.returncode:
        raise Blocked('xcodebuild failed; see '+str(xlog))
    plugin=out/'build/Debug/FSTRPluginOrigin.plugin'
    if not plugin.is_dir(): raise Blocked('Built plugin bundle missing')
    resources=plugin/'Contents/Resources'; resources.mkdir(parents=True,exist_ok=True)
    receipt={'buildId':build_id,'sourceCommit':manifest['sourceCommit'],'targetAE':'25.6.0.101','diagnosticOnly':True}
    (resources/'FSTRPluginOriginBuild.json').write_text(json.dumps(receipt,indent=2)+'\n')
    run(['codesign','--force','--sign','-',str(plugin)])
    run(['codesign','--verify','--strict',str(plugin)])
    binary=plugin/'Contents/MacOS/FSTRPluginOrigin'
    nm=subprocess.run(['nm','-gU',str(binary)],capture_output=True,text=True,check=True)
    if ' _EntryPointFunc' not in nm.stdout: raise Blocked('EntryPointFunc export missing')
    receipt['pluginBinarySha256']=sha256(binary)
    (out/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    archive=out/'FSTRPluginOrigin.zip'
    run(['/usr/bin/ditto','-c','-k','--keepParent',str(plugin),str(archive)])
    (out/'SHA256.txt').write_text(sha256(archive)+'  '+archive.name+'\n')
    print('BUILD PASS:',plugin)
    if not args.yes:
        answer=input('Install diagnostic plugin into Adobe Common MediaCore folder? [y/N] ').strip().lower()
        if answer not in ('y','yes'):
            print('Build complete; installation skipped.')
            return 0
    targets=json.loads((ROOT/'plugin_origin_targets.json').read_text())
    dest=Path(targets['pluginInstallPath'])
    backup=None
    if dest.exists():
        sidecar=dest/'Contents/Resources/FSTRPluginOriginBuild.json'
        if not sidecar.is_file():
            raise Blocked('Refusing to replace an existing plugin without FSTR diagnostic receipt: '+str(dest))
        backup=out/('backup-'+dest.name)
        run(['sudo','/usr/bin/ditto',str(dest),str(backup)])
    run(['sudo','/bin/mkdir','-p',str(dest.parent)])
    if dest.exists(): run(['sudo','/bin/rm','-rf',str(dest)])
    run(['sudo','/usr/bin/ditto',str(plugin),str(dest)])
    installed=dest/'Contents/Resources/FSTRPluginOriginBuild.json'
    if not installed.is_file(): raise Blocked('Install verification failed')
    installed_receipt=json.loads(installed.read_text())
    if installed_receipt.get('buildId')!=build_id: raise Blocked('Installed Build ID mismatch')
    install_receipt={'installedPath':str(dest),'buildId':build_id,'sourceCommit':manifest['sourceCommit'],
                     'backupPath':str(backup) if backup else None,'installedAt':datetime.now(timezone.utc).isoformat()}
    (out_root/'plugin-origin-install.json').write_text(json.dumps(install_receipt,indent=2)+'\n')
    print('INSTALL PASS:',dest)
    print('Now fully restart After Effects, open a saved test comp with at least one layer, then run Observe.command.')
    return 0

def exact_identity(app,targets):
    app,binary,meta=collect_app.identity(app)
    if (meta.get('bundleId')!=targets['aeBundleId'] or meta.get('shortVersion')!=targets['aeShortVersion'] or
        meta.get('bundleVersion')!=targets['aeBundleVersion']):
        raise Blocked('Observer is pinned to exact AE 25.6.0.101')
    return app,binary,meta

def find_pid(binary):
    done=subprocess.run(['/bin/ps','-axo','pid=,comm='],capture_output=True,text=True,timeout=10)
    if done.returncode: raise Blocked('Could not enumerate processes')
    expected=str(Path(binary).resolve()); hits=[]
    for line in done.stdout.splitlines():
        m=re.match(r'^\s*(\d+)\s+(.*)$',line)
        if m and m.group(2).strip()==expected: hits.append(int(m.group(1)))
    if len(hits)!=1: raise Blocked('Expected exactly one selected AE process')
    return hits[0]

def _as_string(v): return str(v).replace('\\','\\\\').replace('"','\\"')
def _bounded(v):
    if v is None:return ''
    if isinstance(v,bytes):v=v.decode('utf-8','replace')
    return str(v).strip()[:4000]

def run_jsx(bundle_id,script_path,timeout=15):
    script='tell application id "'+_as_string(bundle_id)+'" to DoScriptFile POSIX file "'+_as_string(str(script_path))+'"'
    started=time.monotonic()
    try:
        done=subprocess.run(['/usr/bin/osascript','-e',script],capture_output=True,text=True,timeout=timeout)
        return {'ok':done.returncode==0,'elapsedMs':round((time.monotonic()-started)*1000,3),
                'stdout':_bounded(done.stdout),'stderr':_bounded(done.stderr)}
    except (subprocess.TimeoutExpired,OSError) as e:
        return {'ok':False,'elapsedMs':round((time.monotonic()-started)*1000,3),'stdout':'','stderr':str(e)[:4000]}

def snapshot(bundle_id,workspace):
    workspace=Path(workspace).resolve(); workspace.mkdir(parents=True,exist_ok=True,mode=0o700)
    shot=workspace/('snapshot-'+uuid.uuid4().hex[:12]); shot.mkdir(mode=0o700)
    script=shot/'FSTR-Snapshot.jsx'; shutil.copyfile(ROOT/'FSTR-Snapshot.jsx',script)
    output=shot/'state.txt'; (shot/'snapshot-target.txt').write_text(str(output)+'\n')
    bridge=run_jsx(bundle_id,script)
    if not bridge['ok'] or output.is_symlink() or not output.is_file() or output.stat().st_size>65536:
        return {'ok':False,'value':'','error':bridge.get('stderr') or 'snapshot output invalid'}
    value=output.read_text(encoding='utf-8')
    return {'ok':bool(value and value!='0'),'value':value,'error':''}

def parse_state(value):
    out={}
    for part in str(value).split('|'):
        if '=' in part:
            k,v=part.split('=',1); out[k]=v
    return out

def l1_video_active(snapshot_result):
    if not snapshot_result.get('ok'):
        return None
    state=parse_state(snapshot_result.get('value',''))
    if not state.get('comp') or not state.get('L1'):
        return None
    fields=state['L1'].split(',')
    if len(fields)<5 or fields[4] not in ('0','1'):
        return None
    return fields[4]

def read_jsonl(path):
    if not Path(path).is_file(): return []
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]

def wait_for_new_mutation(log_path, build_id, after_sequence, process, timeout=60):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        rows=read_jsonl(log_path)
        matches=[r for r in rows
                 if r.get('kind')=='mutationEnd'
                 and r.get('buildId')==build_id
                 and int(r.get('sequence',0))>int(after_sequence)]
        if matches:
            return matches[-1]
        if process.poll() is not None:
            raise Blocked('Observer ended before helper mutation was observed')
        time.sleep(.05)
    raise Blocked('Timed out waiting for Window → FSTR Plugin Origin Test mutation')

def observe(args):
    manifest=load_manifest(); targets=json.loads((ROOT/'plugin_origin_targets.json').read_text())
    app=Path(args.app).expanduser() if args.app else collect_app.choose_app()
    app,binary,meta=exact_identity(app,targets); pid=find_pid(binary)
    dest=Path(targets['pluginInstallPath'])
    receipt_path=dest/'Contents/Resources/FSTRPluginOriginBuild.json'
    plugin_binary=dest/'Contents/MacOS/FSTRPluginOrigin'
    if not receipt_path.is_file() or not plugin_binary.is_file(): raise Blocked('Diagnostic helper is not installed')
    receipt=json.loads(receipt_path.read_text())
    if not receipt.get('diagnosticOnly') or receipt.get('targetAE')!='25.6.0.101': raise Blocked('Installed helper receipt invalid')
    build_id=receipt.get('buildId'); source_commit=receipt.get('sourceCommit')
    expected_helper_commit=targets.get('acceptedHelperSourceCommit')
    if expected_helper_commit and source_commit!=expected_helper_commit:
        raise Blocked('Installed helper source commit is not accepted by this observer kit')
    log_path=Path('/tmp')/('FSTRPluginOrigin-'+str(pid)+'-'+str(build_id)+'.jsonl')
    deadline=time.monotonic()+10
    while time.monotonic()<deadline and not log_path.is_file(): time.sleep(.1)
    if not log_path.is_file(): raise Blocked('Plugin provenance log not found; helper may not be loaded. Restart AE after install.')
    initial_log=read_jsonl(log_path)
    if not any(r.get('kind')=='loaded' and r.get('buildId')==build_id and r.get('statusCode')==0 for r in initial_log):
        raise Blocked('Helper loaded record missing or failed')
    initial_sequence=max((int(r.get('sequence',0)) for r in initial_log if r.get('buildId')==build_id), default=0)
    modules=[]
    for key,spec in targets['modules'].items():
        p=(app/spec['relativePath']).resolve(strict=True)
        if sha256(p)!=spec['sha256']: raise Blocked('Module hash mismatch: '+key)
        modules.append({'key':key,'path':str(p),'sha256':spec['sha256'],'uuid':spec['uuid']})
    output=Path.home()/'Desktop/FSTR-AE-Research'; output.mkdir(parents=True,exist_ok=True)
    work=Path(tempfile.mkdtemp(prefix='fstr-plugin-origin-',dir=str(output))); os.chmod(work,0o700)
    control=work/'control.jsonl'; ack=work/'ack.jsonl'
    for p in (control,ack):
        fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600); os.close(fd)
    plan={'schemaVersion':1,'runId':'pluginorigin_'+uuid.uuid4().hex,'pid':pid,'executable':str(binary),
          'modules':modules,'breakpoints':targets['breakpoints'],'durationSeconds':targets['durationSeconds'],
          'maxFrames':targets['maxFrames'],'maxEvents':2000,'controlPath':str(control),'ackPath':str(ack),
          'tracePath':str(work/'trace.jsonl'),'resultPath':str(work/'result.json')}
    (work/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    call='script runtime_control.run(lldb.debugger, '+json.dumps(str(work/'plan.json'))+')'
    lldb_log=work/'lldb.log'; evidence=work/'evidence.jsonl'; sequence=0
    before=snapshot(targets['aeBundleId'],work/'snapshots')
    before_l1=l1_video_active(before)
    if before_l1 is None:
        raise Blocked('Preflight requires an active composition with at least one readable layer. Click/open the test comp in AE, then run Observe again.')
    print('Preflight PASS: active comp + L1 state='+before_l1)
    with lldb_log.open('w') as stream:
        proc=subprocess.Popen(['xcrun','lldb','--batch','--no-lldbinit',
          '-o','command script import '+str(ROOT/'trace_callback.py'),
          '-o','command script import '+str(ROOT/'runtime_protocol.py'),
          '-o','command script import '+str(ROOT/'runtime_control.py'),'-o',call],
          stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,text=True)
        runtime_protocol.wait_for_record(ack,kind='ready',sequence=0,process=proc,timeout=targets['attachReadyTimeoutSeconds'])
        def mark(label):
            nonlocal sequence
            sequence+=1; runtime_protocol.send_phase(control,ack,sequence,label,proc,timeout=targets['ackTimeoutSeconds'])
        mark('plugin-origin-start')
        print('In After Effects choose ONCE: Window → FSTR Plugin Origin Test')
        print('Terminal will detect the helper mutation automatically. Do NOT press Enter.')
        observed_mutation=wait_for_new_mutation(
            log_path,build_id,initial_sequence,proc,
            timeout=int(targets.get('mutationTimeoutSeconds',60)))
        print('Helper mutation detected. Waiting briefly for downstream AE processing...')
        time.sleep(float(targets.get('downstreamGraceSeconds',1.5)))
        mark('plugin-origin-done')
        sequence+=1; runtime_protocol.send_finish(control,sequence)
        try: proc.wait(timeout=targets['shutdownTimeoutSeconds'])
        except subprocess.TimeoutExpired:
            proc.terminate(); proc.wait(timeout=3)
    result=json.loads((work/'result.json').read_text()) if (work/'result.json').is_file() else {}
    if result.get('status')!='PASS' or not result.get('detached'): raise Blocked('Observer did not PASS/clean-detach')
    after=snapshot(targets['aeBundleId'],work/'snapshots')
    trace=read_jsonl(work/'trace.jsonl'); plugin_log=read_jsonl(log_path)
    phases={r['label']:r for r in trace if r.get('kind')=='phase'}
    start=phases.get('plugin-origin-start',{}).get('wallTimeNs'); end=phases.get('plugin-origin-done',{}).get('wallTimeNs')
    if not start or not end: raise Blocked('Action phase boundaries missing')
    mutations=[r for r in plugin_log if r.get('kind')=='mutationEnd' and start<=r.get('wallTimeNs',0)<=end and r.get('buildId')==build_id]
    if observed_mutation.get('wallTimeNs',0)<start or observed_mutation.get('wallTimeNs',0)>end:
        raise Blocked('Detected helper mutation fell outside observer action window')
    hits=[r for r in trace if r.get('kind')=='candidate-hit' and start<=r.get('wallTimeNs',0)<=end]
    counts=Counter(r.get('label') for r in hits)
    mutation=mutations[-1] if mutations else None
    after_l1=l1_video_active(after)
    provenance_ok=bool(mutation and mutation.get('statusCode')==0 and mutation.get('beforeVideoActive')!=mutation.get('afterVideoActive'))
    state_ok=bool(
        mutation and before_l1 in ('0','1') and after_l1 in ('0','1')
        and before_l1==str(mutation.get('beforeVideoActive'))
        and after_l1==str(mutation.get('afterVideoActive'))
        and before_l1!=after_l1
    )
    direct_ok=counts.get('layer-switch-internal',0)>0 and counts.get('after-process-from-render-thread',0)>0 and counts.get('process-project-changes-return',0)>0
    analysis={'pluginBuildId':build_id,'pluginSourceCommit':source_commit,
              'installedPluginBinarySha256':sha256(plugin_binary),'provenanceMutation':mutation,
              'stateBeforeL1VideoActive':before_l1,'stateAfterL1VideoActive':after_l1,
              'stateMatchesHelperMutation':state_ok,
              'directHitCounts':dict(counts),'provenance':'OBSERVED' if provenance_ok else 'UNPROVEN',
              'stateChange':'OBSERVED' if state_ok else 'UNPROVEN','directChannel':'OBSERVED' if direct_ok else 'UNPROVEN',
              'otherPluginOrigin':'OBSERVED' if provenance_ok and state_ok and direct_ok else 'UNPROVEN'}
    safe={'schemaVersion':1,'kind':'plugin-origin-provenance','status':'PASS','application':meta,
          'collectorBuild':manifest,'helperReceipt':receipt,'analysis':analysis,
          'limitations':['Helper is a separate diagnostic AEGP built from public SDK, not production FSTR.',
                         'Exact internal observer addresses remain target-build research leads.',
                         'One successful helper mutation proves provenance for this tested plugin-origin scenario, not every third-party plugin implementation.'],
          'SYNC-001':'NOT RUN'}
    runtime_protocol.append_jsonl(evidence,{'kind':'snapshot-before','snapshot':before})
    runtime_protocol.append_jsonl(evidence,{'kind':'snapshot-after','snapshot':after})
    runtime_protocol.append_jsonl(evidence,{'kind':'plugin-log-window','rows':[r for r in plugin_log if start<=r.get('wallTimeNs',0)<=end]})
    runtime_protocol.append_jsonl(evidence,{'kind':'analysis','analysis':analysis})
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:12]
    archive=output/('FSTR-AE-PluginOrigin-'+run_id+'.zip')
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('summary.json',json.dumps(collect_app.redact(safe),indent=2)+'\n')
        z.write(work/'trace.jsonl','trace.jsonl'); z.write(evidence,'evidence.jsonl'); z.write(work/'result.json','result.json')
        z.writestr('helper-log.jsonl','\n'.join(json.dumps(r) for r in plugin_log)+'\n')
        z.writestr('lldb-log.txt',collect_app.redact(lldb_log.read_text(errors='replace'))[-1024*1024:])
    Path(str(archive)+'.sha256').write_text(sha256(archive)+'  '+archive.name+'\n')
    print(('PASS' if analysis['otherPluginOrigin']=='OBSERVED' else 'BLOCKED')+': '+str(archive))
    return 0 if analysis['otherPluginOrigin']=='OBSERVED' else 2

def uninstall(args):
    load_manifest(); targets=json.loads((ROOT/'plugin_origin_targets.json').read_text()); dest=Path(targets['pluginInstallPath'])
    if not dest.exists():
        print('Diagnostic plugin is not installed.'); return 0
    sidecar=dest/'Contents/Resources/FSTRPluginOriginBuild.json'
    if not sidecar.is_file(): raise Blocked('Refusing to remove plugin without FSTR diagnostic receipt')
    receipt=json.loads(sidecar.read_text())
    if not receipt.get('diagnosticOnly') or not str(receipt.get('buildId','')).startswith('fstr-plugin-origin-'):
        raise Blocked('Refusing to remove plugin with invalid diagnostic receipt')
    if not args.yes:
        answer=input('Remove FSTR Plugin Origin diagnostic plugin? [y/N] ').strip().lower()
        if answer not in ('y','yes'): return 0
    run(['sudo','/bin/rm','-rf',str(dest)])
    print('UNINSTALL PASS. Restart After Effects to unload the helper.')
    return 0

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='cmd',required=True)
    b=sub.add_parser('build-install'); b.add_argument('--sdk'); b.add_argument('--yes',action='store_true')
    o=sub.add_parser('observe'); o.add_argument('--app')
    u=sub.add_parser('uninstall'); u.add_argument('--yes',action='store_true')
    args=p.parse_args()
    if args.cmd=='build-install': return build_install(args)
    if args.cmd=='observe': return observe(args)
    return uninstall(args)

if __name__=='__main__':
    try: raise SystemExit(main())
    except (Blocked,ValueError,RuntimeError,TimeoutError,subprocess.CalledProcessError,subprocess.TimeoutExpired) as e:
        print('BLOCKED: '+str(e),file=sys.stderr); raise SystemExit(2)
