import importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[2]
SPEC=importlib.util.spec_from_file_location('plugin_origin_tool',ROOT/'research/ae-notifications/plugin_origin_tool.py')
p=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(p)

class PluginOriginTests(unittest.TestCase):
    def test_source_uses_public_layer_flag_path_and_exact_abi(self):
        src=(ROOT/'native/plugin-origin/PluginOrigin.cpp').read_text()
        for needle in ('AEGP_GetActiveItem','AEGP_GetCompFromItem','AEGP_GetCompLayerByIndex',
                       'AEGP_GetLayerFlags','AEGP_SetLayerFlag','AEGP_LayerFlag_VIDEO_ACTIVE',
                       'AEGP_StartUndoGroup','AEGP_EndUndoGroup','AEGP_PluginInitFunc'):
            self.assertIn(needle,src)
        self.assertNotIn('EvaluateExpression',src)
        self.assertNotIn('AEGP_ExecuteScript',src)

    def test_parse_state_layer1_video_flag(self):
        state=p.parse_state('comp=A|L1=Layer,0,0,1,1,0,0,1')
        self.assertEqual(state['L1'].split(',')[4],'1')

    def test_l1_video_active_requires_active_comp(self):
        self.assertIsNone(p.l1_video_active({'ok':True,'value':'NO_ACTIVE_COMP'}))
        self.assertIsNone(p.l1_video_active({'ok':True,'value':'comp=A|layers=0'}))
        self.assertEqual(p.l1_video_active({'ok':True,'value':'comp=A|L1=Layer,0,0,1,1,0,0,1'}),'1')

    def test_l1_video_active_rejects_invalid_flag(self):
        self.assertIsNone(p.l1_video_active({'ok':True,'value':'comp=A|L1=Layer,0,0,1,x,0,0,1'}))

    def test_wait_for_new_mutation_ignores_historical_rows(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'helper.jsonl'
            path.write_text(
                json.dumps({'kind':'mutationEnd','buildId':'b','sequence':3,'wallTimeNs':10})+'\n',
                encoding='utf-8')
            class Proc:
                def poll(self): return None
            calls={'n':0}
            original=p.read_jsonl
            def fake_read(target):
                calls['n']+=1
                rows=original(target)
                if calls['n']==2:
                    with target.open('a',encoding='utf-8') as f:
                        f.write(json.dumps({'kind':'mutationEnd','buildId':'b','sequence':4,'wallTimeNs':20})+'\n')
                    rows=original(target)
                return rows
            with mock.patch.object(p,'read_jsonl',side_effect=fake_read), mock.patch.object(p.time,'sleep',return_value=None):
                row=p.wait_for_new_mutation(path,'b',3,Proc(),timeout=1)
            self.assertEqual(row['sequence'],4)

    def test_wait_for_new_mutation_detects_child_exit(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'helper.jsonl'; path.write_text('',encoding='utf-8')
            class Proc:
                def poll(self): return 2
            with self.assertRaises(p.Blocked):
                p.wait_for_new_mutation(path,'b',0,Proc(),timeout=1)

    def test_find_sdk_root_accepts_parent(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'sdk'; (root/'Examples/Headers').mkdir(parents=True)
            (root/'Examples/AEGP/Commando/Mac/Commando.xcodeproj').mkdir(parents=True)
            (root/'Examples/Headers/AE_GeneralPlug.h').write_text('fixture')
            self.assertEqual(p.find_sdk_root(Path(td)),root.resolve())

if __name__=='__main__': unittest.main()
