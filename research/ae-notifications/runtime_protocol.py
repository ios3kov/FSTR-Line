"""Parent-process terminal protocol and small JSONL IPC helpers for runtime research."""
from __future__ import annotations
import json, os, re, time
from pathlib import Path

LABEL_RE=re.compile(r'[A-Za-z0-9_-]{1,80}')

def _validate_label(label):
    if not isinstance(label,str) or not LABEL_RE.fullmatch(label):
        raise ValueError('Invalid phase label')
    return label

def append_jsonl(path,row):
    path=Path(path)
    if path.is_symlink():
        raise ValueError('IPC path must not be a symlink')
    payload=(json.dumps(row,ensure_ascii=True,separators=(',',':'))+'\n').encode('utf-8')
    fd=os.open(path,os.O_WRONLY|os.O_APPEND|os.O_CREAT|getattr(os,'O_NOFOLLOW',0),0o600)
    try:
        info=os.fstat(fd)
        if not os.path.isfile(path):
            raise ValueError('IPC path must be a regular file')
        os.write(fd,payload)
        os.fsync(fd)
    finally:
        os.close(fd)

def read_complete_jsonl(path):
    path=Path(path)
    if not path.exists():
        return []
    if path.is_symlink() or not path.is_file():
        raise ValueError('IPC path must be a regular file')
    data=path.read_text(encoding='utf-8')
    if data and not data.endswith('\n'):
        data=data.rsplit('\n',1)[0]+'\n' if '\n' in data else ''
    rows=[]
    for line in data.splitlines():
        if not line:
            continue
        row=json.loads(line)
        if not isinstance(row,dict):
            raise ValueError('IPC row must be an object')
        rows.append(row)
    return rows

def wait_for_record(path,*,kind=None,sequence=None,process=None,timeout=30):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        for row in read_complete_jsonl(path):
            if kind is not None and row.get('kind')!=kind:
                continue
            if sequence is not None and row.get('sequence')!=sequence:
                continue
            return row
        if process is not None and process.poll() is not None:
            raise RuntimeError('LLDB ended before protocol acknowledgement')
        time.sleep(0.05)
    raise TimeoutError('Timed out waiting for runtime protocol acknowledgement')

def send_phase(control_path,ack_path,sequence,label,process,timeout):
    _validate_label(label)
    append_jsonl(control_path,{'kind':'phase','sequence':sequence,'label':label})
    row=wait_for_record(ack_path,kind='phase-ack',sequence=sequence,process=process,timeout=timeout)
    if row.get('label')!=label:
        raise RuntimeError('Phase acknowledgement label mismatch')

def send_finish(control_path,sequence):
    append_jsonl(control_path,{'kind':'finish','sequence':sequence})

def send_abort(control_path,sequence,reason='user-abort'):
    append_jsonl(control_path,{'kind':'abort','sequence':sequence,'reason':str(reason)[:200]})

def run_user_steps(phases,send_phase_callback,*,input_fn=input,output_fn=print):
    if not isinstance(phases,list) or not phases:
        raise ValueError('Interactive phases are required')
    normalized=[]
    for phase in phases:
        if not isinstance(phase,dict):
            raise ValueError('Invalid interactive phase')
        label=_validate_label(phase.get('label'))
        instruction=phase.get('instructionRu')
        if not isinstance(instruction,str) or not instruction.strip() or len(instruction)>500:
            raise ValueError('Invalid interactive instruction')
        normalized.append((label,instruction.strip()))
    total=len(normalized)
    for index,(label,instruction) in enumerate(normalized,1):
        send_phase_callback(label+'-start')
        output_fn('')
        output_fn(f'ШАГ {index}/{total}')
        output_fn(instruction)
        input_fn('Сделай действие в After Effects, вернись в Terminal и нажми Enter → ')
        send_phase_callback(label+'-done')
