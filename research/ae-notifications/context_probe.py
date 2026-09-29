#!/usr/bin/env python3
"""Narrow real-AE positive control for active composition and post-processing boundaries."""
from __future__ import annotations
import argparse, hashlib, json, os, plistlib, re, shutil, subprocess, sys, tempfile, time, uuid, zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import collect_app
import runtime_protocol

TOOLS=('Context-AE.command','context_probe.py','context_targets.json',
       'runtime_control.py','trace_callback.py','runtime_protocol.py','collect_app.py',
       'FSTR-Snapshot.jsx','FSTR-PostCommit-Marker.jsx')

class Blocked(Exception): pass

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def verify_kit():
    manifest=json.loads((ROOT/'build-manifest.json').read_text(encoding='utf-8'))
    if manifest.get('sourceState')!='clean' or set(manifest.get('files',{}))!=set(TOOLS):
        raise ValueError('Invalid context-probe kit manifest')
    for name in TOOLS:
        p=ROOT/name
        if p.is_symlink() or not p.is_file() or sha256(p)!=manifest['files'][name]:
            raise ValueError('Context-probe kit hash mismatch: '+name)
    return manifest

def exact_identity(app,targets):
    app,binary,meta=collect_app.identity(app)
    if (meta.get('bundleId')!=targets['aeBundleId'] or
        meta.get('shortVersion')!=targets['aeShortVersion'] or
        meta.get('bundleVersion')!=targets['aeBundleVersion']):
        raise Blocked('Context probe is pinned to exact AE 25.6.0.101')
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

def _as_string(v):
    return str(v).replace('\\','\\\\').replace('"','\\"')

def _bounded(v):
    if v is None: return ''
    if isinstance(v,bytes): v=v.decode('utf-8','replace')
    return str(v).strip()[:4000]

def run_jsx(bundle_id,script_path,timeout=30):
    script='tell application id "'+_as_string(bundle_id)+'" to DoScriptFile POSIX file "'+_as_string(str(script_path))+'"'
    started=time.monotonic()
    try:
        done=subprocess.run(['/usr/bin/osascript','-e',script],capture_output=True,text=True,timeout=timeout)
        return {'ok':done.returncode==0,'timedOut':False,
                'elapsedMs':round((time.monotonic()-started)*1000,3),
                'stdout':_bounded(done.stdout),'stderr':_bounded(done.stderr),
                'returnCode':done.returncode}
    except subprocess.TimeoutExpired as e:
        return {'ok':False,'timedOut':True,'elapsedMs':round((time.monotonic()-started)*1000,3),
                'stdout':_bounded(e.stdout),'stderr':_bounded(e.stderr),'returnCode':None,
                'error':'DoScriptFile timed out'}
    except OSError as e:
        return {'ok':False,'timedOut':False,'elapsedMs':round((time.monotonic()-started)*1000,3),
                'stdout':'','stderr':str(e)[:4000],'returnCode':None,'error':'DoScriptFile launch failed'}

def snapshot(bundle_id,workspace):
    workspace=Path(workspace).resolve(); workspace.mkdir(parents=True,exist_ok=True,mode=0o700)
    shot=workspace/('snapshot-'+uuid.uuid4().hex[:12]); shot.mkdir(mode=0o700)
    script=shot/'FSTR-Snapshot.jsx'; shutil.copyfile(ROOT/'FSTR-Snapshot.jsx',script)
    output=shot/'state.txt'; (shot/'snapshot-target.txt').write_text(str(output)+'\n',encoding='utf-8')
    bridge=run_jsx(bundle_id,script,timeout=15)
    value=''; error=bridge.get('stderr',''); ok=False
    if bridge.get('ok'):
        try:
            if output.is_symlink() or not output.is_file(): raise ValueError('snapshot output not created')
            resolved=output.resolve(strict=True)
            if not resolved.is_relative_to(shot.resolve()): raise ValueError('snapshot escaped owned directory')
            if output.stat().st_size>65536: raise ValueError('snapshot exceeded 64 KiB')
            value=output.read_text(encoding='utf-8')
            if not value or value=='0': raise ValueError('snapshot output invalid')
            ok=True
        except (OSError,ValueError) as e:
            error=str(e)
    return {'ok':ok,'value':value,'error':error,'bridgeOk':bool(bridge.get('ok')),
            'elapsedMs':bridge.get('elapsedMs'),'timedOut':bool(bridge.get('timedOut'))}

def parse_state(value):
    parts={}
    for piece in str(value).split('|'):
        if '=' in piece:
            k,v=piece.split('=',1); parts[k]=v
    return parts

def run_marker(bundle_id,workspace):
    root=Path(workspace).resolve()/('marker-'+uuid.uuid4().hex[:12]); root.mkdir(parents=True,mode=0o700)
    script=root/'FSTR-PostCommit-Marker.jsx'; shutil.copyfile(ROOT/'FSTR-PostCommit-Marker.jsx',script)
    output=root/'marker.txt'; (root/'marker-target.txt').write_text(str(output)+'\n',encoding='utf-8')
    bridge=run_jsx(bundle_id,script,timeout=30)
    rows=[]
    if output.is_file() and not output.is_symlink() and output.stat().st_size<=65536:
        for line in output.read_text(encoding='utf-8').splitlines():
            fields=line.split('|')
            if len(fields)>=2 and fields[1].isdigit():
                rows.append({'label':fields[0],'wallTimeMs':int(fields[1]),'detail':'|'.join(fields[2:])})
    return {'bridge':bridge,'markers':rows}

def rows(path):
    if not Path(path).is_file(): return []
    return [json.loads(x) for x in Path(path).read_text(encoding='utf-8').splitlines() if x.strip()]

def phase_windows(trace):
    starts={}; out={}
    for r in trace:
        if r.get('kind')!='phase': continue
        label=r.get('label','')
        if label.endswith('-start'): starts[label[:-6]]=r['monotonicNs']
        elif label.endswith('-done') and label[:-5] in starts:
            out[label[:-5]]=(starts[label[:-5]],r['monotonicNs'])
    return out

def analyze(trace,evidence,marker):
    windows=phase_windows(trace)
    hits=[r for r in trace if r.get('kind')=='candidate-hit']
    result={'windows':{},'activeComp':'UNPROVEN','stateOracle':'UNPROVEN','postProcessing':'UNPROVEN'}
    snap={}
    for e in evidence:
        if e.get('kind') in ('snapshot-before','snapshot-after'):
            snap[(e['phase'],e['kind'])]=e['snapshot']
    for name,(start,end) in windows.items():
        wh=[h for h in hits if start<=h.get('monotonicNs',0)<=end]
        result['windows'][name]={'hits':len(wh),'counts':dict(Counter(h.get('label') for h in wh))}
    valid=[v for v in snap.values() if v.get('ok') and v.get('value') not in ('','0')]
    if valid: result['stateOracle']='OBSERVED'
    switches=[]
    for name in ('comp-switch','comp-switch-back'):
        b=snap.get((name,'snapshot-before'),{}); a=snap.get((name,'snapshot-after'),{})
        if b.get('ok') and a.get('ok'):
            bc=parse_state(b['value']).get('comp'); ac=parse_state(a['value']).get('comp')
            counts=result['windows'].get(name,{}).get('counts',{})
            active_hits=sum(v for k,v in counts.items() if k.startswith('pano-comp-') or k.startswith('pano-item-') or k.startswith('item-activate') or k.startswith('item-deactivate') or k=='activate-item-panel-ctor')
            switches.append(bool(bc and ac and bc!=ac and active_hits>0))
    if switches and all(switches): result['activeComp']='OBSERVED'
    after_end=next((m['wallTimeMs'] for m in marker.get('markers',[]) if m['label']=='after-end-undo'),None)
    if after_end is not None:
        script_window=windows.get('script-postcommit')
        if script_window:
            wh=[h for h in hits if script_window[0]<=h.get('monotonicNs',0)<=script_window[1]]
            returns=[h for h in wh if h.get('label')=='process-project-changes-return']
            boundaries=[h for h in wh if h.get('label')=='after-process-from-render-thread']
            after_ret=any(h.get('wallTimeNs',0)>=after_end*1000000 for h in returns)
            after_bound=any(h.get('wallTimeNs',0)>=after_end*1000000 for h in boundaries)
            result['postProcessing']='OBSERVED_AFTER_SCRIPT_END_UNDO' if after_ret and after_bound else 'UNPROVEN'
            result['markerComparison']={'afterEndUndoMs':after_end,'returnAfter':after_ret,'boundaryAfter':after_bound}
    return result

def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument('--app',type=Path); ap.add_argument('--output',type=Path,default=Path.home()/'Desktop/FSTR-AE-Research')
    args=ap.parse_args(argv)
    manifest=verify_kit(); targets=json.loads((ROOT/'context_targets.json').read_text())
    app=args.app.expanduser() if args.app else collect_app.choose_app()
    app,binary,meta=exact_identity(app,targets)
    modules=[]
    for key,spec in targets['modules'].items():
        p=(app/spec['relativePath']).resolve(strict=True)
        if not p.is_relative_to(app) or p.is_symlink(): raise Blocked('Unsafe module path')
        digest=sha256(p)
        if digest!=spec['sha256']: raise Blocked('Module hash mismatch: '+key)
        modules.append({'key':key,'path':str(p),'sha256':digest,'uuid':spec['uuid']})
    pid=find_pid(binary)
    output=args.output.expanduser().resolve(); output.mkdir(parents=True,exist_ok=True)
    work=Path(tempfile.mkdtemp(prefix='fstr-context-',dir=str(output))); os.chmod(work,0o700)
    control=work/'control.jsonl'; ack=work/'ack.jsonl'
    for p in (control,ack):
        fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600); os.close(fd)
    plan={'schemaVersion':1,'runId':'context_'+uuid.uuid4().hex,'pid':pid,'executable':str(binary),
          'modules':modules,'breakpoints':targets['breakpoints'],'durationSeconds':targets['durationSeconds'],
          'maxFrames':targets['maxFrames'],'maxEvents':10000,'controlPath':str(control),'ackPath':str(ack),
          'tracePath':str(work/'trace.jsonl'),'resultPath':str(work/'result.json')}
    (work/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    call='script runtime_control.run(lldb.debugger, '+json.dumps(str(work/'plan.json'))+')'
    log=work/'lldb.log'; evidence=work/'evidence.jsonl'
    sequence=0; marker_result={'bridge':{'ok':False},'markers':[]}
    with log.open('w',encoding='utf-8') as stream:
        proc=subprocess.Popen(['xcrun','lldb','--batch','--no-lldbinit',
            '-o','command script import '+str(ROOT/'trace_callback.py'),
            '-o','command script import '+str(ROOT/'runtime_protocol.py'),
            '-o','command script import '+str(ROOT/'runtime_control.py'),'-o',call],
            stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,text=True)
        runtime_protocol.wait_for_record(ack,kind='ready',sequence=0,process=proc,timeout=targets['attachReadyTimeoutSeconds'])
        print('FSTR Context/PostCommit Probe — узкий тест, без restart.')
        print('Нужны две уже открытые композиции и хотя бы один слой.')
        def mark(label):
            nonlocal sequence
            sequence+=1
            runtime_protocol.send_phase(control,ack,sequence,label,proc,timeout=targets['ackTimeoutSeconds'])
        try:
            for index,phase in enumerate(targets['phases'],1):
                before=snapshot(targets['aeBundleId'],work/'snapshots')
                runtime_protocol.append_jsonl(evidence,{'kind':'snapshot-before','phase':phase['label'],'snapshot':before})
                mark(phase['label']+'-start')
                print('\nШАГ %d/%d'%(index,len(targets['phases'])))
                print(phase['instructionRu'])
                if phase['kind']=='marker-script':
                    input('Нажми Enter → ')
                    marker_result=run_marker(targets['aeBundleId'],work/'markers')
                    runtime_protocol.append_jsonl(evidence,{'kind':'marker-script','phase':phase['label'],'result':marker_result})
                    if not marker_result['bridge'].get('ok'):
                        print('Marker-script не завершился автоматически; этот post-processing subgate будет BLOCKED.')
                else:
                    input('Сделай действие в AE, вернись в Terminal и нажми Enter → ')
                mark(phase['label']+'-done')
                after=snapshot(targets['aeBundleId'],work/'snapshots')
                runtime_protocol.append_jsonl(evidence,{'kind':'snapshot-after','phase':phase['label'],'snapshot':after})
            sequence+=1; runtime_protocol.send_finish(control,sequence)
        except BaseException as e:
            if proc.poll() is None:
                try:
                    sequence+=1; runtime_protocol.send_abort(control,sequence,type(e).__name__)
                except Exception: pass
            raise
        finally:
            try: proc.wait(timeout=targets['shutdownTimeoutSeconds'])
            except subprocess.TimeoutExpired:
                proc.terminate()
                try: proc.wait(timeout=3)
                except subprocess.TimeoutExpired: proc.kill(); proc.wait()
    result=json.loads((work/'result.json').read_text()) if (work/'result.json').exists() else {}
    if result.get('status')!='PASS' or not result.get('detached'):
        raise Blocked('Context observer did not PASS/clean-detach: '+json.dumps(result))
    trace_rows=rows(work/'trace.jsonl'); evidence_rows=rows(evidence)
    analysis=analyze(trace_rows,evidence_rows,marker_result)
    safe={'schemaVersion':1,'kind':'context-postcommit-probe','status':'PASS','application':meta,
          'collectorBuild':manifest,'analysis':analysis,
          'corrections':{'DoProcessProjectChangesEntry':'0x7af9f4',
                         'AfterProcessFromRenderThreadBoundary':'0x7afa7c',
                         'DoProcessProjectChangesReturn':'0x7b055c'},
          'limitations':['Private internal addresses are exact-build research only.',
                         'OBSERVED_AFTER_SCRIPT_END_UNDO is timing evidence for the tested script origin, not universal native post-commit proof.',
                         'Active-comp acceptance requires both snapshot comp-name change and exact activation-candidate hit.'],
          'SYNC-001':'NOT RUN'}
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:12]
    archive=output/('FSTR-AE-Context-'+run_id+'.zip')
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('summary.json',json.dumps(collect_app.redact(safe),indent=2)+'\n')
        z.write(work/'trace.jsonl','trace.jsonl'); z.write(evidence,'evidence.jsonl')
        z.write(work/'result.json','result.json')
        z.writestr('lldb-log.txt',collect_app.redact(log.read_text(encoding='utf-8',errors='replace'))[-1024*1024:])
    Path(str(archive)+'.sha256').write_text(sha256(archive)+'  '+archive.name+'\n')
    print('\nPASS: '+str(archive))
    return 0

if __name__=='__main__':
    try: raise SystemExit(main())
    except (Blocked,ValueError,RuntimeError,TimeoutError,subprocess.TimeoutExpired) as e:
        print('BLOCKED: '+str(e),file=sys.stderr); raise SystemExit(2)
