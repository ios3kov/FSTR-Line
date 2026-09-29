"""Interactive terminal protocol for AE runtime research. No target-process access."""
from __future__ import annotations
import re
import select

def _valid_label(value):
    return isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,80}',value)

def _wait_readline(tty,timeout):
    ready,_,_=select.select([tty],[],[],timeout)
    if not ready:
        raise TimeoutError('Interactive step timed out')
    line=tty.readline()
    if line=='':
        raise RuntimeError('Interactive terminal closed')
    return line

def run_interactive_phases(phases,mark_phase,*,tty=None,start_timeout=60,step_timeout=60,wait_readline=_wait_readline):
    """Prompt one action at a time; next phase starts only after Enter."""
    if not isinstance(phases,list) or not phases:
        raise ValueError('Interactive phases are required')
    for phase in phases:
        if not isinstance(phase,dict) or not _valid_label(phase.get('label')):
            raise ValueError('Invalid interactive phase')
        instruction=phase.get('instructionRu')
        if not isinstance(instruction,str) or not instruction.strip() or len(instruction)>500:
            raise ValueError('Invalid interactive instruction')
    owned=False
    if tty is None:
        tty=open('/dev/tty','r+',encoding='utf-8',buffering=1)
        owned=True
    try:
        tty.write('\nFSTR Runtime — интерактивный режим.\n')
        tty.write('Оставь After Effects открытым. Вернись в Terminal и нажми Enter, когда готов начать тест.\n> ')
        tty.flush()
        wait_readline(tty,start_timeout)
        total=len(phases)
        for index,phase in enumerate(phases,1):
            label=phase['label']
            mark_phase(label+'-start')
            tty.write(f'\nШАГ {index}/{total}\n{phase["instructionRu"]}\n')
            tty.write('Сделай это в After Effects. Когда закончишь — вернись в Terminal и нажми Enter.\n> ')
            tty.flush()
            wait_readline(tty,step_timeout)
            mark_phase(label+'-done')
        tty.write('\nВсе действия записаны. Завершаю наблюдение и отключаю debugger...\n')
        tty.flush()
    finally:
        if owned:
            tty.close()
