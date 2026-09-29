#!/usr/bin/env python3
"""One-run final AE notification research matrix: native, script, stress, restart/reopen."""
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys, tempfile, time, uuid, zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import collect_app
import runtime_protocol

TOOLS=('Runtime-AE.command','runtime_probe.py','runtime_control.py','trace_callback.py',
       'runtime_protocol.py','runtime_candidates.json','collect_app.py',
       'FSTR-Snapshot.jsx','FSTR-ExtendScript-Origin.jsx','FSTR-Burst.jsx')

class Blocked(Exception): pass

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def verify_kit():
    manifest=json.loads((ROOT/'build-manifest.json').read_text(encoding='utf-8'))
    if manifest.get('sourceState')!='clean' or set(manifest.get('files',{}))!=set(TOOLS):
        raise ValueError('Invalid runtime kit manifest')
    for name in TOOLS:
        path=ROOT/name
        if path.is_symlink() or not path.is_file() or sha256(path)!=manifest['files'][name]:
            raise ValueError('Runtime kit hash mismatch')
    return manifest

def exact_identity(app,candidates):
    app,binary,meta=collect_app.identity(app)
    if (meta['bundleId']!=candidates['aeBundleId'] or
        meta['shortVersion']!=candidates['aeShortVersion'] or
        meta['bundleVersion']!=candidates['aeBundleVersion']):
        raise Blocked('Final matrix is pinned to exact AE 25.6.0.101')
    return app,binary,meta

def find_pids(binary,runner=subprocess.run):
    done=runner(['/bin/ps','-axo','pid=,comm='],capture_output=True,text=True,timeout=10)
    if done.returncode: raise Blocked('Could not enumerate local processes')
    expected=str(Path(binary).resolve()); matches=[]
    for line in done.stdout.splitlines():
        m=re.match(r'^\s*(\d+)\s+(.*)$',line)
        if m and m.group(2).strip()==expected:
            matches.append(int(m.group(1)))
    return matches

def require_one_pid(binary):
    pids=find_pids(binary)
    if len(pids)!=1: raise Blocked('Expected exactly one running selected After Effects process')
    return pids[0]

def wait_for_pid_count(binary,count,timeout):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        pids=find_pids(binary)
        if len(pids)==count: return pids
        time.sleep(.25)
    raise Blocked('Timed out waiting for After Effects process state')

def redact(value): return collect_app.redact(value)

def _make_file(path):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600); os.close(fd)

def _as_string(value):
    return str(value).replace('\\','\\\\').replace('"','\\"')

def run_jsx(bundle_id,script_path,timeout=30):
    script='tell application id "'+_as_string(bundle_id)+'" to DoScriptFile POSIX file "'+_as_string(str(script_path))+'"'
    started=time.monotonic()
    done=subprocess.run(['/usr/bin/osascript','-e',script],capture_output=True,text=True,timeout=timeout)
    return {'ok':done.returncode==0,'elapsedMs':round((time.monotonic()-started)*1000,3),
            'stdout':done.stdout.strip()[:4000],'stderr':done.stderr.strip()[:4000],
            'returnCode':done.returncode}

def snapshot(bundle_id):
    row=run_jsx(bundle_id,ROOT/'FSTR-Snapshot.jsx',timeout=15)
    return {'ok':row['ok'],'value':row['stdout'],'error':row['stderr'],
            'elapsedMs':row['elapsedMs']}

def append_evidence(path,row):
    runtime_protocol.append_jsonl(path,dict(row,wallTimeNs=time.time_ns(),monotonicNs=time.monotonic_ns()))

def run_observer_session(binary,pid,modules,candidates,phases,work,session_name,evidence_path):
    session=work/session_name; session.mkdir()
    control=session/'control.jsonl'; ack=session/'ack.jsonl'; _make_file(control); _make_file(ack)
    plan={'schemaVersion':1,'runId':'runtime_'+uuid.uuid4().hex,'pid':pid,
          'executable':str(binary),'modules':modules,'breakpoints':candidates['breakpoints'],
          'durationSeconds':int(candidates['durationSeconds']),'maxFrames':int(candidates.get('maxFrames',8)),
          'maxEvents':10000,'controlPath':str(control),'ackPath':str(ack),
          'tracePath':str(session/'trace.jsonl'),'resultPath':str(session/'result.json')}
    (session/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    call='script runtime_control.run(lldb.debugger, '+json.dumps(str(session/'plan.json'))+')'
    log_path=session/'lldb.log'
    with log_path.open('w',encoding='utf-8') as log_stream:
        proc=subprocess.Popen(['xcrun','lldb','--batch','--no-lldbinit',
            '-o','command script import '+str(ROOT/'trace_callback.py'),
            '-o','command script import '+str(ROOT/'runtime_protocol.py'),
            '-o','command script import '+str(ROOT/'runtime_control.py'),'-o',call],
            stdin=subprocess.DEVNULL,stdout=log_stream,stderr=subprocess.STDOUT,text=True)
        runtime_protocol.wait_for_record(ack,kind='ready',sequence=0,process=proc,
            timeout=int(candidates.get('attachReadyTimeoutSeconds',30)))
        print('\nDebugger подключён. '+session_name+'.')
        sequence=0
        bundle_id=candidates['aeBundleId']
        def mark(label):
            nonlocal sequence
            sequence+=1
            runtime_protocol.send_phase(control,ack,sequence,label,proc,
                timeout=int(candidates.get('ackTimeoutSeconds',10)))
        try:
            total=len(phases)
            for index,phase in enumerate(phases,1):
                before=snapshot(bundle_id)
                append_evidence(evidence_path,{'kind':'snapshot-before','session':session_name,
                    'phase':phase['label'],'snapshot':before})
                mark(phase['label']+'-start')
                print('\nШАГ %d/%d [%s]'%(index,total,session_name))
                print(phase['instructionRu'])
                kind=phase.get('kind','manual')
                if kind in ('jsx','burst'):
                    input('Нажми Enter → ')
                    script_result=run_jsx(bundle_id,ROOT/phase['script'],timeout=60)
                    append_evidence(evidence_path,{'kind':'script-result','session':session_name,
                        'phase':phase['label'],'script':phase['script'],'result':script_result})
                    if not script_result['ok']:
                        print('Автозапуск ExtendScript не сработал. Запусти вручную: '+str(ROOT/phase['script']))
                        input('После ручного запуска вернись сюда и нажми Enter → ')
                else:
                    input('Сделай действие в After Effects, вернись в Terminal и нажми Enter → ')
                mark(phase['label']+'-done')
                after=snapshot(bundle_id)
                append_evidence(evidence_path,{'kind':'snapshot-after','session':session_name,
                    'phase':phase['label'],'snapshot':after,'changed':before.get('value')!=after.get('value')
                        if before.get('ok') and after.get('ok') else None})
            sequence+=1; runtime_protocol.send_finish(control,sequence)
        except BaseException as error:
            if proc.poll() is None:
                try:
                    sequence+=1; runtime_protocol.send_abort(control,sequence,type(error).__name__)
                except Exception: pass
            raise
        finally:
            try: proc.wait(timeout=int(candidates.get('shutdownTimeoutSeconds',30)))
            except subprocess.TimeoutExpired:
                proc.terminate()
                try: proc.wait(timeout=3)
                except subprocess.TimeoutExpired: proc.kill(); proc.wait()
    if not (session/'result.json').exists():
        raise Blocked('LLDB session ended without result: '+session_name)
    result=json.loads((session/'result.json').read_text())
    if result.get('status')!='PASS' or not result.get('detached'):
        raise Blocked('Observer session did not PASS cleanly: '+session_name+' '+json.dumps(result))
    return result

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app',type=Path); parser.add_argument('--choose-app',action='store_true')
    parser.add_argument('--output',type=Path,default=Path.home()/'Desktop/FSTR-AE-Research')
    args=parser.parse_args(argv)
    manifest=verify_kit(); candidates=json.loads((ROOT/'runtime_candidates.json').read_text())
    app=args.app.expanduser() if args.app else collect_app.choose_app()
    app,binary,meta=exact_identity(app,candidates)
    modules=[]
    for key,spec in candidates['modules'].items():
        path=(app/spec['relativePath']).resolve(strict=True)
        if not path.is_relative_to(app) or path.is_symlink(): raise Blocked('Unsafe module path')
        actual=sha256(path)
        if actual!=spec['sha256']: raise Blocked('Module hash changed: '+key)
        modules.append({'key':key,'path':str(path),'sha256':actual,'uuid':spec['uuid']})
    output=args.output.expanduser().resolve(); output.mkdir(parents=True,exist_ok=True)
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:12]
    work=Path(tempfile.mkdtemp(prefix='fstr-final-',dir=str(output))); os.chmod(work,0o700)
    evidence=work/'evidence.jsonl'; _make_file(evidence)

    print('FSTR FINAL MATRIX — один запуск. Native + ExtendScript + stress + restart/reopen.')
    print('Перед началом: тестовый проект должен быть СОХРАНЁН; желательно две композиции и минимум два слоя.')
    input('Когда готов — нажми Enter → ')

    baseline=run_jsx(candidates['aeBundleId'],ROOT/'FSTR-Burst.jsx',timeout=60)
    append_evidence(evidence,{'kind':'performance-baseline','result':baseline})
    if not baseline['ok']:
        print('Baseline ExtendScript не запустился автоматически; performance сравнение будет BLOCKED.')

    pid=require_one_pid(binary)
    run_observer_session(binary,pid,modules,candidates,candidates['preRestart'],work,'pre-restart',evidence)

    print('\n=== RESTART / REOPEN ===')
    print('Сохрани тестовый проект и ЗАКРОЙ After Effects полностью вручную. Скрипт AE не закрывает.')
    input('Когда After Effects полностью закрыт — нажми Enter → ')
    wait_for_pid_count(binary,0,30)
    print('Теперь снова открой тот же After Effects 25.6.0.101 и этот же сохранённый тестовый проект.')
    input('Когда проект открыт и таймлайн виден — нажми Enter → ')
    new_pid=wait_for_pid_count(binary,1,45)[0]
    append_evidence(evidence,{'kind':'restart-observed','oldPid':pid,'newPid':new_pid,
                              'pidChanged':pid!=new_pid})
    run_observer_session(binary,new_pid,modules,candidates,candidates['postRestart'],work,'post-restart',evidence)

    observed_burst=[r for r in runtime_protocol.read_complete_jsonl(evidence)
                    if r.get('kind')=='script-result' and r.get('phase')=='extendscript-burst']
    perf={'baselineMs':baseline.get('elapsedMs') if baseline.get('ok') else None,
          'observedMs':observed_burst[0]['result'].get('elapsedMs') if observed_burst else None}
    if perf['baselineMs'] and perf['observedMs']:
        perf['ratio']=round(perf['observedMs']/perf['baselineMs'],3)
    append_evidence(evidence,{'kind':'performance-comparison',**perf})

    safe={'schemaVersion':1,'kind':'final-runtime-matrix','status':'PASS','application':meta,
          'collectorBuild':manifest,'sessions':['pre-restart','post-restart'],
          'performance':perf,
          'limitations':['Other-plugin origin is only exercised if the user has a third-party plugin that changes AE state.',
                         'Snapshot-after-action proves observed final state, not that DoProcessProjectChanges entry is itself post-commit.',
                         'Breakpoint multiplicity is raw evidence; it is not yet classified as duplicate notification semantics.'],
          'SYNC-001':'NOT RUN'}
    archive=output/('FSTR-AE-FinalMatrix-'+run_id+'.zip')
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('summary.json',json.dumps(redact(safe),indent=2)+'\n')
        z.write(evidence,'evidence.jsonl')
        for session_name in ('pre-restart','post-restart'):
            session=work/session_name
            z.write(session/'trace.jsonl',session_name+'/trace.jsonl')
            z.write(session/'result.json',session_name+'/result.json')
            log=redact((session/'lldb.log').read_text(encoding='utf-8',errors='replace'))
            z.writestr(session_name+'/lldb-log.txt',log[-1024*1024:])
    digest=sha256(archive); Path(str(archive)+'.sha256').write_text(digest+'  '+archive.name+'\n')
    for child in sorted(work.rglob('*'),reverse=True):
        if child.is_file(): child.unlink()
        elif child.is_dir(): child.rmdir()
    work.rmdir()
    print('\nPASS: '+str(archive))
    return 0

if __name__=='__main__':
    try: raise SystemExit(main())
    except (Blocked,ValueError,RuntimeError,TimeoutError,subprocess.TimeoutExpired) as error:
        print('BLOCKED: '+str(error),file=sys.stderr); raise SystemExit(2)
