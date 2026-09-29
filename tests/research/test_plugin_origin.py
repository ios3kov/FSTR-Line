import importlib.util,json,tempfile,unittest
from pathlib import Path
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

    def test_find_sdk_root_accepts_parent(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'sdk'; (root/'Examples/Headers').mkdir(parents=True)
            (root/'Examples/AEGP/Commando/Mac/Commando.xcodeproj').mkdir(parents=True)
            (root/'Examples/Headers/AE_GeneralPlug.h').write_text('fixture')
            self.assertEqual(p.find_sdk_root(Path(td)),root.resolve())

if __name__=='__main__': unittest.main()
