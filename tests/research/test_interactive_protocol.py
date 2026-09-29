import io
import importlib.util
from pathlib import Path
import unittest

MODULE=Path(__file__).resolve().parents[2]/'research/ae-notifications/interactive_prompt.py'
spec=importlib.util.spec_from_file_location('interactive_prompt',MODULE)
protocol=importlib.util.module_from_spec(spec); spec.loader.exec_module(protocol)

class InteractiveProtocolTests(unittest.TestCase):
    def test_every_action_waits_for_enter_and_marks_start_done(self):
        tty=io.StringIO('\n\n\n')
        marks=[]
        phases=[
            {'label':'one','instructionRu':'Сделай первое действие.'},
            {'label':'two','instructionRu':'Сделай второе действие.'},
        ]
        protocol.run_interactive_phases(
            phases,marks.append,tty=tty,start_timeout=1,step_timeout=1,
            wait_readline=lambda stream,timeout: stream.readline())
        self.assertEqual(marks,['one-start','one-done','two-start','two-done'])
        output=tty.getvalue()
        self.assertIn('ШАГ 1/2',output)
        self.assertIn('нажми Enter',output)

    def test_timeout_stops_before_next_phase(self):
        tty=io.StringIO()
        marks=[]
        with self.assertRaises(TimeoutError):
            protocol.run_interactive_phases(
                [{'label':'one','instructionRu':'Действие.'}],marks.append,tty=tty,
                wait_readline=lambda stream,timeout: (_ for _ in ()).throw(TimeoutError('fixture')))
        self.assertEqual(marks,[])

    def test_invalid_phase_rejected_before_prompt(self):
        tty=io.StringIO('\n')
        with self.assertRaises(ValueError):
            protocol.run_interactive_phases(
                [{'label':'bad label','instructionRu':'Действие.'}],lambda x:None,tty=tty)

if __name__=='__main__': unittest.main()
