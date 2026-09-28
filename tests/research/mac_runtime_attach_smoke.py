"""Mac-only attach smoke for runtime observer using an owned fixture, never Adobe."""
import hashlib,json,re,subprocess,sys,tempfile,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def _symbol_file_address(binary,name):
    text=subprocess.check_output(['xcrun','nm','-nm',str(binary)],text=True,timeout=30)
    for line in text.splitlines():
        if line.rstrip().endswith(' '+name):
            match=re.match(r'^([0-9A-Fa-f]+)\s',line)
            if match:
                return int(match.group(1),16)
    raise RuntimeError('Fixture symbol address unavailable: '+name)

def main():
    if sys.platform!='darwin':
        raise SystemExit('BLOCKED')
    commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    archive=ROOT/'dist/runtime-research'/commit/'FSTR-AE-Runtime.zip'
    with tempfile.TemporaryDirectory(prefix='fstr-runtime-smoke-') as td:
        t=Path(td)
        with zipfile.ZipFile(archive) as z:
            z.extractall(t/'kit')
        kit=t/'kit/FSTR-AE-Runtime'
        src=t/'fixture.cpp'
        src.write_text(
            '#include <unistd.h>\n'
            'extern "C" __attribute__((noinline)) void fstr_runtime_candidate(){}\n'
            'int main(){for(int i=0;i<2000;i++){fstr_runtime_candidate(); usleep(20000);} return 0;}\n'
        )
        binary=t/'fstr-runtime-fixture'
        subprocess.run(['xcrun','clang++','-g','-O0',str(src),'-o',str(binary)],check=True,timeout=60)
        uuid_text=subprocess.check_output(['xcrun','dwarfdump','--uuid',str(binary)],text=True)
        match=re.search(r'UUID: ([A-Fa-f0-9-]{36})',uuid_text)
        if not match:
            raise RuntimeError('Fixture UUID unavailable')
        uid=match.group(1)
        digest=hashlib.sha256(binary.read_bytes()).hexdigest()
        file_address=_symbol_file_address(binary,'_fstr_runtime_candidate')
        process=subprocess.Popen([str(binary)])
        try:
            time.sleep(0.1)
            plan={
                'runId':'fixture','pid':process.pid,'executable':str(binary),
                'modules':[{'key':'fixture','path':str(binary),'sha256':digest,'uuid':uid}],
                'breakpoints':[{'label':'fixture-event','module':'fixture',
                                'fileAddress':hex(file_address),'minLocations':1,'maxLocations':1}],
                'phases':[{'offsetSeconds':0,'label':'owned-fixture','instruction':'fixture'}],
                'durationSeconds':2,'maxEvents':500,
                'tracePath':str(t/'trace.jsonl'),'resultPath':str(t/'result.json')
            }
            (t/'plan.json').write_text(json.dumps(plan),encoding='utf-8')
            call='script runtime_control.run(lldb.debugger, '+json.dumps(str(t/'plan.json'))+')'
            done=subprocess.run(
                ['xcrun','lldb','--batch','--no-lldbinit',
                 '-o','command script import '+str(kit/'trace_callback.py'),
                 '-o','command script import '+str(kit/'runtime_control.py'),
                 '-o',call],
                capture_output=True,text=True,timeout=30
            )
            if not (t/'result.json').exists():
                raise RuntimeError('No result: '+done.stdout+done.stderr)
            result=json.loads((t/'result.json').read_text())
            if result['status']!='PASS':
                raise RuntimeError(json.dumps(result)+'\n'+done.stdout+done.stderr)
            rows=[json.loads(x) for x in (t/'trace.jsonl').read_text().splitlines()]
            hits=[r for r in rows if r['kind']=='candidate-hit']
            if not hits:
                raise RuntimeError('No owned-fixture breakpoint hits')
            if any(r['isNotificationProven'] or r['commitPhase']!='UNKNOWN' for r in hits):
                raise RuntimeError('Observer overclaimed semantics')
            bp=result['breakpoints'][0]
            if bp.get('fileAddress')!=hex(file_address) or bp.get('resolvedFileAddress')!=hex(file_address):
                raise RuntimeError('Exact file-address breakpoint identity was not preserved')
            if not result.get('detached'):
                raise RuntimeError('Observer did not confirm detach')
            evidence={
                'status':'PASS','scope':'exact-address attach to owned fixture only, NOT AE',
                'hits':len(hits),'sourceCommit':commit,'detached':True,
                'fileAddress':hex(file_address),'SYNC-001':'NOT RUN'
            }
            out=ROOT/'dist/notification-evidence/runtime-attach-smoke.json'
            out.parent.mkdir(parents=True,exist_ok=True)
            out.write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
            print(json.dumps(evidence))
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

if __name__=='__main__':
    main()
