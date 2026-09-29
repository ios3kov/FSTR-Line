"""Mac-only parent/LLDB IPC attach smoke using an owned fixture, never Adobe."""
import hashlib,importlib.util,json,re,subprocess,sys,tempfile,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def _symbol_file_address(binary,name):
    text=subprocess.check_output(['xcrun','nm','-nm',str(binary)],text=True,timeout=30)
    for line in text.splitlines():
        if line.rstrip().endswith(' '+name):
            match=re.match(r'^([0-9A-Fa-f]+)\s',line)
            if match: return int(match.group(1),16)
    raise RuntimeError('Fixture symbol address unavailable: '+name)

def _load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

def main():
    if sys.platform!='darwin': raise SystemExit('BLOCKED')
    commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    archive=ROOT/'dist/runtime-research'/commit/'FSTR-AE-Runtime.zip'
    with tempfile.TemporaryDirectory(prefix='fstr-runtime-smoke-') as td:
        t=Path(td)
        with zipfile.ZipFile(archive) as z: z.extractall(t/'kit')
        kit=t/'kit/FSTR-AE-Runtime'
        protocol=_load(kit/'runtime_protocol.py','fixture_runtime_protocol')
        src=t/'fixture.cpp'
        src.write_text('#include <unistd.h>\nextern "C" __attribute__((noinline)) void fstr_runtime_candidate(){}\nint main(){for(int i=0;i<2000;i++){fstr_runtime_candidate(); usleep(20000);} return 0;}\n')
        binary=t/'fstr-runtime-fixture'
        subprocess.run(['xcrun','clang++','-g','-O0',str(src),'-o',str(binary)],check=True,timeout=60)
        uuid_text=subprocess.check_output(['xcrun','dwarfdump','--uuid',str(binary)],text=True)
        match=re.search(r'UUID: ([A-Fa-f0-9-]{36})',uuid_text)
        if not match: raise RuntimeError('Fixture UUID unavailable')
        uid=match.group(1); digest=hashlib.sha256(binary.read_bytes()).hexdigest()
        file_address=_symbol_file_address(binary,'_fstr_runtime_candidate')
        target_process=subprocess.Popen([str(binary)])
        try:
            time.sleep(0.1)
            control=t/'control.jsonl'; ack=t/'ack.jsonl'; control.touch(); ack.touch()
            plan={'runId':'fixture','pid':target_process.pid,'executable':str(binary),
                  'modules':[{'key':'fixture','path':str(binary),'sha256':digest,'uuid':uid}],
                  'breakpoints':[{'label':'fixture-event','role':'boundary-candidate','module':'fixture',
                                  'fileAddress':hex(file_address),'minLocations':1,'maxLocations':1}],
                  'durationSeconds':10,'maxEvents':500,'maxFrames':4,
                  'controlPath':str(control),'ackPath':str(ack),
                  'tracePath':str(t/'trace.jsonl'),'resultPath':str(t/'result.json')}
            (t/'plan.json').write_text(json.dumps(plan),encoding='utf-8')
            call='script runtime_control.run(lldb.debugger, '+json.dumps(str(t/'plan.json'))+')'
            log=(t/'lldb.log').open('w',encoding='utf-8')
            lldb_process=subprocess.Popen(
                ['xcrun','lldb','--batch','--no-lldbinit',
                 '-o','command script import '+str(kit/'trace_callback.py'),
                 '-o','command script import '+str(kit/'runtime_protocol.py'),
                 '-o','command script import '+str(kit/'runtime_control.py'),'-o',call],
                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,text=True)
            try:
                protocol.wait_for_record(ack,kind='ready',sequence=0,process=lldb_process,timeout=10)
                protocol.send_phase(control,ack,1,'fixture-start',lldb_process,5)
                time.sleep(.5)
                protocol.send_phase(control,ack,2,'fixture-done',lldb_process,5)
                protocol.send_finish(control,3)
                lldb_process.wait(timeout=15)
            finally:
                log.close()
                if lldb_process.poll() is None:
                    lldb_process.terminate(); lldb_process.wait(timeout=3)
            if not (t/'result.json').exists():
                raise RuntimeError('No runtime result: '+(t/'lldb.log').read_text())
            result=json.loads((t/'result.json').read_text())
            if result['status']!='PASS' or not result.get('detached'):
                raise RuntimeError(json.dumps(result)+'\n'+(t/'lldb.log').read_text())
            rows=[json.loads(x) for x in (t/'trace.jsonl').read_text().splitlines()]
            hits=[r for r in rows if r['kind']=='candidate-hit']
            phases=[r.get('label') for r in rows if r['kind']=='phase']
            if not hits: raise RuntimeError('No owned-fixture breakpoint hits')
            if 'fixture-start' not in phases or 'fixture-done' not in phases:
                raise RuntimeError('Parent/LLDB phase IPC did not reach trace')
            if any(r['isNotificationProven'] or r['commitPhase']!='UNKNOWN' for r in hits):
                raise RuntimeError('Observer overclaimed semantics')
            evidence={'status':'PASS','scope':'parent-terminal/LLDB IPC on owned fixture only, NOT AE',
                      'hits':len(hits),'sourceCommit':commit,'detached':True,
                      'phaseIPC':'PASS','SYNC-001':'NOT RUN'}
            out=ROOT/'dist/notification-evidence/runtime-attach-smoke.json'
            out.parent.mkdir(parents=True,exist_ok=True)
            out.write_text(json.dumps(evidence,indent=2)+'\n'); print(json.dumps(evidence))
        finally:
            if target_process.poll() is None:
                target_process.terminate()
                try: target_process.wait(timeout=2)
                except subprocess.TimeoutExpired: target_process.kill(); target_process.wait()

if __name__=='__main__': main()
