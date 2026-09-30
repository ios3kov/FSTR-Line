import importlib.util,json,tempfile,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SPEC=importlib.util.spec_from_file_location("matrix_analyzer",ROOT/"research/ae-notifications/analyze_runtime_matrix.py")
m=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(m)

class MatrixAnalyzerTests(unittest.TestCase):
    def test_orders_windows_and_flags_later_marker(self):
        rows=[
          {"kind":"phase","label":"x-start","monotonicNs":10},
          {"kind":"candidate-hit","label":"process-project-changes","monotonicNs":20},
          {"kind":"candidate-hit","label":"end-group","monotonicNs":30},
          {"kind":"phase","label":"x-done","monotonicNs":40},
        ]
        out=m.analyze_session(rows)["windows"]["x"]
        self.assertFalse(out["lastProcessProjectChangesAfterKnownMarkers"])
        self.assertEqual(out["knownMarkersAfterLastProcessProjectChanges"][0]["label"],"end-group")

    def test_idle_and_script_gates_from_fixture_zip(self):
        summary={"status":"PASS","collectorBuild":{"sourceCommit":"fixture"}}
        pre=[
          {"kind":"phase","label":"idle-control-start","monotonicNs":1},
          {"kind":"phase","label":"idle-control-done","monotonicNs":2},
          {"kind":"phase","label":"native-comp-switch-start","monotonicNs":3},
          {"kind":"phase","label":"native-comp-switch-done","monotonicNs":4},
          {"kind":"phase","label":"extendscript-origin-start","monotonicNs":5},
          {"kind":"candidate-hit","label":"process-project-changes","monotonicNs":6},
          {"kind":"phase","label":"extendscript-origin-done","monotonicNs":7},
          {"kind":"phase","label":"other-plugin-origin-start","monotonicNs":8},
          {"kind":"phase","label":"other-plugin-origin-done","monotonicNs":9},
        ]
        post=[
          {"kind":"phase","label":"restart-extendscript-start","monotonicNs":1},
          {"kind":"candidate-hit","label":"process-project-changes","monotonicNs":2},
          {"kind":"phase","label":"restart-extendscript-done","monotonicNs":3},
        ]
        evidence=[{"kind":"restart-observed","pidChanged":True},
                  {"kind":"snapshot-before","snapshot":{"ok":True,"value":"0"}}]
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"m.zip"
            with zipfile.ZipFile(p,"w") as z:
                z.writestr("summary.json",json.dumps(summary))
                z.writestr("evidence.jsonl","\n".join(json.dumps(x) for x in evidence)+"\n")
                for name,rows in (("pre-restart",pre),("post-restart",post)):
                    z.writestr(name+"/trace.jsonl","\n".join(json.dumps(x) for x in rows)+"\n")
                    z.writestr(name+"/result.json",json.dumps({"status":"PASS","pid":1}))
            report=m.analyze(p)
        # This historical-shaped fixture has no parent or complete capture lifecycle.
        # Preserve raw hits, but do not credit them to a verified runtime session.
        self.assertEqual(report["runtimeStatus"],"BLOCKED")
        self.assertEqual(report["observations"]["extendScriptProcessProjectChanges"],[1,1])
        self.assertEqual(report["gates"]["extendScriptOrigin"],"UNPROVEN")
        self.assertEqual(report["gates"]["activeCompSwitch"],"UNPROVEN")
        self.assertEqual(report["gates"]["postCommitSemantics"],"UNPROVEN")
        self.assertEqual(report["gates"]["restartReopen"],"UNPROVEN")

if __name__=="__main__": unittest.main()
