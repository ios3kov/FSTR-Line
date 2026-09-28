import importlib.util,json
from pathlib import Path
import tempfile,types,unittest
MODULE=Path(__file__).resolve().parents[2]/'research/ae-notifications/trace_callback.py'
spec=importlib.util.spec_from_file_location('trace_callback',MODULE)
trace=importlib.util.module_from_spec(spec); spec.loader.exec_module(trace)
UID='01234567-89ab-cdef-0123-456789abcdef'
def frame(pid=42,uid=UID):
    process=types.SimpleNamespace(GetProcessID=lambda:pid)
    thread=types.SimpleNamespace(GetProcess=lambda:process,GetThreadID=lambda:7)
    module=types.SimpleNamespace(GetUUIDString=lambda:uid)
    address=types.SimpleNamespace(GetModule=lambda:module,GetFileAddress=lambda:0x1234)
    return types.SimpleNamespace(GetThread=lambda:thread,GetPCAddress=lambda:address,
                                 GetFunctionName=lambda:'FixtureOnly_NotAnAECandidate')
def location():
    bp=types.SimpleNamespace(GetID=lambda:1)
    return types.SimpleNamespace(GetBreakpoint=lambda:bp,GetID=lambda:1)
class TraceTests(unittest.TestCase):
    def tearDown(self): trace.stop_capture()
    def test_no_implicit_capture_or_resume(self): self.assertTrue(trace.on_breakpoint(frame(),location(),{}))
    def test_bound_identity_phase_and_no_post_commit_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'trace.jsonl'
            trace.start_capture(path,'fixture',42,{UID:'a'*64},max_events=1)
            trace.mark_phase('native-selection')
            self.assertFalse(trace.on_breakpoint(frame(),location(),{}))
            self.assertTrue(trace.on_breakpoint(frame(),location(),{}))
            trace.stop_capture()
            rows=[json.loads(x) for x in path.read_text().splitlines()]
            self.assertTrue(any(r.get('kind')=='phase' and r.get('label')=='native-selection' for r in rows))
            hit=next(r for r in rows if r['kind']=='candidate-hit')
            self.assertEqual(hit['commitPhase'],'UNKNOWN'); self.assertFalse(hit['isNotificationProven'])
            self.assertTrue(any(r['kind']=='capture-limit' for r in rows))
            self.assertEqual(rows[-1]['SYNC-001'],'NOT RUN')
    def test_invalid_phase(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'trace.jsonl'; trace.start_capture(path,'fixture',42,{UID:'a'*64})
            with self.assertRaises(ValueError): trace.mark_phase('bad phase!')
    def test_wrong_pid_or_module_pauses(self):
        for pid,uid in [(99,UID),(42,'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')]:
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'trace.jsonl'; trace.start_capture(path,'fixture',42,{UID:'a'*64})
                self.assertTrue(trace.on_breakpoint(frame(pid,uid),location(),{})); trace.stop_capture()
                self.assertIn('capture-error',path.read_text())
    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'trace.jsonl'; path.write_text('original')
            with self.assertRaises(FileExistsError): trace.start_capture(path,'fixture',42,{UID:'a'*64})
    def test_validation_precedes_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'trace.jsonl'
            with self.assertRaises(ValueError): trace.start_capture(path,'fixture',42,{UID:'bad'})
            self.assertFalse(path.exists())
if __name__=='__main__': unittest.main()
