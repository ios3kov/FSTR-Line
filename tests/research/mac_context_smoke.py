"""Mac-only packaged context dependencies smoke on owned process. Never Adobe."""
import hashlib,json,re,subprocess,sys,tempfile,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def symbol_address(binary,name):
    text=subprocess.check_output(['xcrun','nm','-nm',str(binary)],text=True)
    for line in text.splitlines():
        if line.rstrip().endswith(' '+name):
            m=re.match(r'^([0-9A-Fa-f]+)\s',line)
            if m: return int(m.group(1),16)
    raise RuntimeError('symbol unavailable')
def main():
    if sys.platform!='darwin': raise SystemExit('BLOCKED')
    commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    archive=ROOT/'dist/context-research'/commit/'FSTR-AE-Context.zip'
    with tempfile.TemporaryDirectory(prefix='fstr-context-smoke-') as td:
        t=Path(td)
        with zipfile.ZipFile(archive) as z: z.extractall(t/'kit')
        kit=t/'kit/FSTR-AE-Context'
        src=t/'f.cpp'; src.write_text('#include <unistd.h>\nextern "C" __attribute__((noinline)) void fstr_context_candidate(){}\nint main(){for(int i=0;i<1000;i++){fstr_context_candidate(); usleep(20000);} return 0;}\n')
        binary=t/'fixture'; subprocess.run(['xcrun','clang++','-g','-O0',str(src),'-o',str(binary)],check=True,timeout=60)
        uuid_text=subprocess.check_output(['xcrun','dwarfdump','--uuid',str(binary)],text=True)
        uid=re.search(r'UUID: ([A-Fa-f0-9-]{36})',uuid_text).group(1)
        digest=hashlib.sha256(binary.read_bytes()).hexdigest(); addr=symbol_address(binary,'_fstr_context_candidate')
        target=subprocess.Popen([str(binary)])
        try:
            time.sleep(.1); control=t/'control'; ack=t/'ack'; control.touch(); ack.touch()
            plan={'runId':'fixture','pid':target.pid,'executable':str(binary),
                  'modules':[{'key':'fixture','path':str(binary),'sha256':digest,'uuid':uid}],
                  'breakpoints':[{'label':'fixture-context','role':'active-comp-candidate','module':'fixture','fileAddress':hex(addr),'minLocations':1,'maxLocations':1}],
                  'durationSeconds':8,'maxFrames':4,'maxEvents':500,'controlPath':str(control),'ackPath':str(ack),
                  'tracePath':str(t/'trace.jsonl'),'resultPath':str(t/'result.json')}
            (t/'plan.json').write_text(json.dumps(plan))
            call='script runtime_control.run(lldb.debugger, '+json.dumps(str(t/'plan.json'))+')'
            log=(t/'lldb.log').open('w')
            proc=subprocess.Popen(['xcrun','lldb','--batch','--no-lldbinit',
                '-o','command script import '+str(kit/'trace_callback.py'),
                '-o','command script import '+str(kit/'runtime_protocol.py'),
                '-o','command script import '+str(kit/'runtime_control.py'),'-o',call],
                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,text=True)
            try:
                sys.path.insert(0,str(kit)); import runtime_protocol
                runtime_protocol.wait_for_record(ack,kind='ready',sequence=0,process=proc,timeout=10)
                runtime_protocol.send_phase(control,ack,1,'fixture-start',proc,5)
                time.sleep(.4)
                runtime_protocol.send_phase(control,ack,2,'fixture-done',proc,5)
                runtime_protocol.send_finish(control,3); proc.wait(timeout=12)
            finally:
                log.close()
            result=json.loads((t/'result.json').read_text())
            rows=[json.loads(x) for x in (t/'trace.jsonl').read_text().splitlines()]
            hits=[x for x in rows if x.get('kind')=='candidate-hit']
            assert result['status']=='PASS' and result['detached'] and hits
            ev={'status':'PASS','scope':'packaged context dependencies exact-address attach on owned fixture, NOT AE',
                'sourceCommit':commit,'hits':len(hits),'SYNC-001':'NOT RUN'}
            dest=ROOT/'dist/notification-evidence/context-smoke.json'; dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(json.dumps(ev,indent=2)+'\n'); print(json.dumps(ev))
        finally:
            if target.poll() is None:
                target.terminate(); target.wait(timeout=3)
if __name__=='__main__': main()
