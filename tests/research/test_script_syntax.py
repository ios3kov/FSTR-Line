import ast
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]

class ResearchScriptSyntaxTests(unittest.TestCase):
    def test_mac_smoke_scripts_parse(self):
        paths=sorted((ROOT/'tests/research').glob('mac_*.py'))
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(path=path.name):
                ast.parse(path.read_text(encoding='utf-8'),filename=str(path))

    def test_research_entrypoints_parse(self):
        paths=[
            ROOT/'research/ae-notifications/runtime_probe.py',
            ROOT/'research/ae-notifications/runtime_control.py',
            ROOT/'research/ae-notifications/focused_static.py',
            ROOT/'research/ae-notifications/trace_callback.py',
        ]
        for path in paths:
            with self.subTest(path=path.name):
                ast.parse(path.read_text(encoding='utf-8'),filename=str(path))

if __name__=='__main__':
    unittest.main()
