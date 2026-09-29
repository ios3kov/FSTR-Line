#!/usr/bin/env python3
"""Prepare and run a bounded observational LLDB trace against an already-running AE test session."""
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys, tempfile, uuid, zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import collect_app
import runtime_protocol

TOOLS=('Runtime-AE.command','runtime_probe.py','runtime_control.py','trace_callback.py',
       'runtime_protocol.py','runtime_candidates.json','collect_app.py')

class Blocked(Exception): pass

def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
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
        raise Blocked('This runtime probe is pinned to the exact AE 25.6.0.101 build from static evidence')
    return app,binary,meta

def find_pid(binary,runner=subprocess.run):
    done=runner(['/bin/ps','-axo','pid=,command='],capture_output=True,text=True,timeout=10)
    if done.returncode: raise Blocked('Could not enumerate local processes')
    expected=str(binary.resolve())
    matches=[]
    for line in done.stdout.splitlines():
        m=re.match(r'^\s*(\d+)\s+(.*)$',line)
        if not m: continue
        command=m.group(2)
        if command==expected or command.startswith(expected+' '):
            matches.append(int(m.group(1)))
    if len(matches)!=1:
        raise Blocked('Expected exactly one running instance of the selected After Effects application')
    return matches[0]

def redact(value):
    return collect_app.redact(value)

def _make_ipc_file(path):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    os.close(fd)

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app',type=Path)
    parser.add_argument('--choose-app',action='store_true')
    parser.add_argument('--pid',type=int)
    parser.add_argument('--output',type=Path,default=Path.home()/'Desktop/FSTR-AE-Research')
    args=parser.parse_args(argv)
    if args.app and args.choose_app: parser.error('Choose one app selection mode')
    manifest=verify_kit()
    candidates=json.loads((ROOT/'runtime_candidates.json').read_text(encoding='utf-8'))
    app=args.app.expanduser() if args.app else collect_app.choose_app()
    app,binary,meta=exact_identity(app,candidates)
    modules=[]
    for key,spec in candidates['modules'].items():
        path=(app/spec['relativePath']).resolve(strict=True)
        if not path.is_relative_to(app) or path.is_symlink(): raise Blocked('Unsafe module path')
        actual=sha256(path)
        if actual!=spec['sha256']: raise Blocked('Module hash changed since static evidence: '+key)
        modules.append({'key':key,'path':str(path),'sha256':actual,'uuid':spec['uuid']})
    pid=args.pid or find_pid(binary)
    if pid==os.getpid(): raise Blocked('Refusing to attach to the probe process')

    output=args.output.expanduser().resolve(); output.mkdir(parents=True,exist_ok=True)
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:12]
    work=Path(tempfile.mkdtemp(prefix='fstr-runtime-',dir=str(output))); os.chmod(work,0o700)
    control_path=work/'control.jsonl'; ack_path=work/'ack.jsonl'
    _make_ipc_file(control_path); _make_ipc_file(ack_path)
    plan={'schemaVersion':1,'runId':'runtime_'+uuid.uuid4().hex,'pid':pid,
          'executable':str(binary),'modules':modules,'breakpoints':candidates['breakpoints'],
          'durationSeconds':int(candidates['durationSeconds']),
          'maxFrames':int(candidates.get('maxFrames',8)),'maxEvents':5000,
          'controlPath':str(control_path),'ackPath':str(ack_path),
          'tracePath':str(work/'trace.jsonl'),'resultPath':str(work/'result.json')}
    (work/'plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')

    print('Attach-only observer. Он не запускает AE и не вызывает private-функции.')
    print('ИНТЕРАКТИВНЫЙ РЕЖИМ: одно действие → вернись в Terminal → Enter → следующий шаг.')
    print('Открой сохранённый тестовый проект; не используй несохранённую рабочую сцену.')

    call='script runtime_control.run(lldb.debugger, '+json.dumps(str(work/'plan.json'))+')'
    log_path=work/'lldb-live.log'
    lldb_process=None
    protocol_error=None
    sequence=0
    try:
        with log_path.open('w',encoding='utf-8') as log_stream:
            lldb_process=subprocess.Popen(
                ['xcrun','lldb','--batch','--no-lldbinit',
                 '-o','command script import '+str(ROOT/'trace_callback.py'),
                 '-o','command script import '+str(ROOT/'runtime_protocol.py'),
                 '-o','command script import '+str(ROOT/'runtime_control.py'),
                 '-o',call],
                stdin=subprocess.DEVNULL,stdout=log_stream,stderr=subprocess.STDOUT,text=True)
            runtime_protocol.wait_for_record(
                ack_path,kind='ready',sequence=0,process=lldb_process,
                timeout=int(candidates.get('attachReadyTimeoutSeconds',30)))
            print('\nDebugger подключён. Теперь шаги идут строго по Enter.')
            def send_marker(label):
                nonlocal sequence
                sequence+=1
                runtime_protocol.send_phase(
                    control_path,ack_path,sequence,label,lldb_process,
                    timeout=int(candidates.get('ackTimeoutSeconds',10)))
            try:
                runtime_protocol.run_user_steps(candidates['phases'],send_marker)
                sequence+=1
                runtime_protocol.send_finish(control_path,sequence)
            except (KeyboardInterrupt,EOFError,Exception) as error:
                protocol_error=error
                if lldb_process.poll() is None:
                    try:
                        sequence+=1
                        runtime_protocol.send_abort(control_path,sequence,type(error).__name__)
                    except Exception:
                        pass
            try:
                lldb_process.wait(timeout=int(candidates.get('shutdownTimeoutSeconds',30)))
            except subprocess.TimeoutExpired:
                lldb_process.terminate()
                try: lldb_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    lldb_process.kill(); lldb_process.wait()
                if protocol_error is None:
                    protocol_error=TimeoutError('LLDB did not finish after interactive protocol')
    finally:
        pass

    result_path=work/'result.json'
    result=json.loads(result_path.read_text()) if result_path.exists() else {
        'status':'BLOCKED','stage':'lldb','error':'LLDB ended without a result','SYNC-001':'NOT RUN'}
    if protocol_error is not None and result.get('status')=='PASS':
        result={'status':'BLOCKED','stage':'parent-protocol','error':str(protocol_error),
                'detached':result.get('detached',False),'SYNC-001':'NOT RUN'}
    safe={'schemaVersion':1,'kind':'runtime-candidate-trace','status':result.get('status'),
          'application':meta,'sourceFocusedReportSha256':candidates['sourceFocusedReportSha256'],
          'collectorBuild':manifest,'runtimeResult':result,
          'limitations':['Breakpoint hits are observations, not notification API proof.',
                         'Terminal prompts are owned by the launcher, not by LLDB.',
                         'Post-commit state and complete SYNC-001 coverage remain separate gates.'],
          'SYNC-001':'NOT RUN'}
    archive=output/('FSTR-AE-Runtime-'+run_id+'.zip')
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('summary.json',json.dumps(redact(safe),indent=2)+'\n')
        if (work/'trace.jsonl').exists():
            z.writestr('trace.jsonl',(work/'trace.jsonl').read_text(encoding='utf-8'))
        if log_path.exists():
            log=redact(log_path.read_text(encoding='utf-8',errors='replace'))
            z.writestr('lldb-log.txt',log[-1024*1024:])
    digest=sha256(archive)
    Path(str(archive)+'.sha256').write_text(digest+'  '+archive.name+'\n')
    for child in work.iterdir(): child.unlink()
    work.rmdir()
    print(result.get('status','BLOCKED')+': '+str(archive))
    return 0 if result.get('status')=='PASS' else 2

if __name__=='__main__':
    raise SystemExit(main())
