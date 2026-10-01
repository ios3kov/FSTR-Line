import io,json,tempfile,types,unittest
from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parents[2]
MODULE=ROOT/'research/ae-notifications/runtime_protocol.py'
spec=importlib.util.spec_from_file_location('runtime_protocol',MODULE)
protocol=importlib.util.module_from_spec(spec); spec.loader.exec_module(protocol)

class RuntimeProtocolTests(unittest.TestCase):
    def test_parent_prompts_one_step_then_enter_then_next(self):
        sent=[]; prompts=[]
        phases=[
            {'label':'one','instructionRu':'Первое действие.'},
            {'label':'two','instructionRu':'Второе действие.'},
        ]
        answers=iter(['',''])
        protocol.run_user_steps(
            phases,sent.append,input_fn=lambda prompt:(prompts.append(prompt),next(answers))[1],
            output_fn=lambda value: prompts.append(value))
        self.assertEqual(sent,['one-start','one-done','two-start','two-done'])
        joined='\n'.join(prompts)
        self.assertIn('ШАГ 1/2',joined); self.assertIn('ШАГ 2/2',joined); self.assertIn('Enter',joined)

    def test_jsonl_phase_ack_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); control=root/'control'; ack=root/'ack'
            control.touch(); ack.touch()
            class Proc:
                def poll(self): return None
            protocol.append_jsonl(ack,{'kind':'phase-ack','sequence':7,'label':'x-start'})
            protocol.send_phase(control,ack,7,'x-start',Proc(),1)
            rows=protocol.read_complete_jsonl(control)
            self.assertEqual(rows,[{'kind':'phase','sequence':7,'label':'x-start'}])

    def test_wait_detects_child_exit(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'ack'; path.touch()
            class Proc:
                def poll(self): return 2
            with self.assertRaises(RuntimeError):
                protocol.wait_for_record(path,kind='ready',sequence=0,process=Proc(),timeout=.2)

    def test_invalid_phase_rejected_before_prompt(self):
        with self.assertRaises(ValueError):
            protocol.run_user_steps([{'label':'bad label','instructionRu':'x'}],lambda _:None)

if __name__=='__main__': unittest.main()
