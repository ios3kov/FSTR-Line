#!/usr/bin/env python3
"""Opt-in owned-comp research. Leaves its test comp in place; never saves/closes AE."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import completion_preflight
import context_probe as context
import runtime_protocol as protocol


def write_new(path, value):
    with path.open('x', encoding='utf-8') as stream:
        stream.write(value)


def execute(work, label, body):
    output = work / (label + '.json')
    script = work / (label + '.jsx')
    footer = ('var f=new File(' + json.dumps(str(output)) + ');'
              'if(!f.open("w"))throw new Error("output refused");'
              'try{f.write("{\\\"compId\\\":"+result.compId+",\\\"layerId\\\":"+result.layerId+'
              '",\\\"enabled\\\":"+(result.enabled?"true":"false")+'
              '(result.name?",\\\"name\\\":\\\""+result.name+"\\\"":"")+"}");}finally{f.close();}')
    write_new(script, '(function(){' + body + footer + '}());')
    bridge = context.run_jsx('com.adobe.AfterEffects.application', script, timeout=20)
    if not bridge.get('ok'):
        raise RuntimeError('Script failed/timed out: ' + label + '; no retry')
    if output.is_symlink() or not output.is_file() or output.stat().st_size > 65536:
        raise RuntimeError('Missing/unsafe output: ' + label)
    return json.loads(output.read_text())


def run(app, pid, output):
    identity = completion_preflight.preflight(app, pid)
    targets = json.loads((ROOT / 'completion_targets.json').read_text())
    # Inspected arm64 setter bodies preserve their context pointer in x19 at
    # these eight exact-build sites. No target memory is dereferenced.
    for point in targets['breakpoints']:
        point['contextRegister']='x19'
    output.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='completion-', dir=output))
    os.chmod(work, 0o700)
    print('Research workspace: ' + str(work), flush=True)
    name = 'FSTR completion test ' + uuid.uuid4().hex[:12]
    setup = execute(work, 'setup',
        'if(!app.project)throw new Error("No project");'
        'var c=app.project.items.addComp(' + json.dumps(name) + ',64,64,1,2,24);'
        'var l=c.layers.addNull();l.name="FSTR owned test layer";'
        'var result={compId:c.id,layerId:l.id,name:c.name,enabled:l.enabled};')
    write_new(work / 'identity.json', json.dumps({'preflight':identity,'fixture':setup}, indent=2))
    if setup.get('name') != name or setup.get('enabled') is not True:
        raise RuntimeError('Fixture identity failed; no attach')
    # Recheck immediately before attach. The user explicitly authorized this session.
    completion_preflight.preflight(app, pid)
    _, binary, _ = context.collect_app.identity(app)
    for filename in ('control.jsonl', 'ack.jsonl'):
        write_new(work / filename, '')
    plan = {'runId':work.name, 'pid':pid, 'executable':str(binary),
            'durationSeconds':90, 'maxEvents':2000, 'maxFrames':4,
            'modules':[{'key':k,'path':str(app / s['relativePath']),
                        'sha256':s['sha256'],'uuid':s['uuid']} for k,s in targets['modules'].items()],
            'breakpoints':targets['breakpoints']}
    for key, filename in (('controlPath','control.jsonl'),('ackPath','ack.jsonl'),
                          ('tracePath','trace.jsonl'),('resultPath','result.json')):
        plan[key] = str(work / filename)
    write_new(work / 'plan.json', json.dumps(plan, indent=2))
    command = ['xcrun','lldb','--batch','--no-lldbinit']
    for module in ('trace_callback','runtime_protocol','runtime_control'):
        command += ['-o','command script import ' + json.dumps(str(ROOT / (module + '.py')))]
    command += ['-o','script runtime_control.run(lldb.debugger, ' + json.dumps(str(work / 'plan.json')) + ')']
    sequence = 0
    with (work / 'lldb.log').open('x') as log:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        try:
            protocol.wait_for_record(work/'ack.jsonl', kind='ready', sequence=0, process=process, timeout=25)
            guard = ('var c=null;for(var i=1;i<=app.project.numItems;i++){'
                     'var x=app.project.item(i);if(x.id===' + str(setup['compId']) + ')c=x;}'
                     'if(!c||c.name!==' + json.dumps(name) + '||c.numLayers!==1)throw new Error("fixture changed");'
                     'var l=c.layer(1);if(l.id!==' + str(setup['layerId']) + ')throw new Error("layer changed");')
            cases = {
                'grouped':'app.beginUndoGroup("FSTR grouped");try{l.enabled=false;l.enabled=true;}finally{app.endUndoGroup();}',
                'separate':'app.beginUndoGroup("FSTR first");try{l.enabled=false;}finally{app.endUndoGroup();}app.beginUndoGroup("FSTR second");try{l.enabled=true;}finally{app.endUndoGroup();}',
                'noop':'app.beginUndoGroup("FSTR noop");try{l.enabled=l.enabled;}finally{app.endUndoGroup();}'
            }
            for label, body in cases.items():
                sequence += 1
                protocol.send_phase(work/'control.jsonl',work/'ack.jsonl',sequence,label+'-start',process,10)
                result = execute(work,label,guard + body + 'var result={compId:c.id,layerId:l.id,enabled:l.enabled};')
                if result.get('enabled') is not True:
                    raise RuntimeError('Unexpected fixture state: ' + label)
                sequence += 1
                protocol.send_phase(work/'control.jsonl',work/'ack.jsonl',sequence,label+'-done',process,10)
            sequence += 1
            protocol.send_finish(work/'control.jsonl',sequence)
        except BaseException:
            if process.poll() is None:
                protocol.send_abort(work/'control.jsonl',sequence+1,'runner-error')
            raise
        finally:
            try:
                process.wait(timeout=35)
            except subprocess.TimeoutExpired:
                # Do not kill AE or silently assume detach. Preserve process/evidence.
                raise RuntimeError('Debugger shutdown unconfirmed; inspect owned LLDB process ' + str(process.pid))
    result = json.loads((work/'result.json').read_text())
    if result.get('status') != 'PASS' or not result.get('detached'):
        raise RuntimeError('Capture/detach not accepted: ' + json.dumps(result))
    print(json.dumps({'observer':'PASS','detached':True,'workspace':str(work),
                      'testComp':name,'SYNC-001':'NOT RUN'}), flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app',type=Path,required=True)
    parser.add_argument('--pid',type=int,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--allow-owned-comp-and-attach',action='store_true',required=True)
    args=parser.parse_args()
    run(args.app.resolve(),args.pid,args.output.resolve())
