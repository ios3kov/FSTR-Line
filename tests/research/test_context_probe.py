import importlib.util,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SPEC=importlib.util.spec_from_file_location('context_probe',ROOT/'research/ae-notifications/context_probe.py')
c=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(c)

class ContextProbeTests(unittest.TestCase):
    def test_parse_state_extracts_comp(self):
        self.assertEqual(c.parse_state('comp=A|layers=2|time=1.0')['comp'],'A')

    def test_active_comp_requires_state_change_and_candidate_hit(self):
        trace=[
          {'kind':'phase','label':'comp-switch-start','monotonicNs':10},
          {'kind':'candidate-hit','label':'pano-comp-activate','monotonicNs':20,'wallTimeNs':100},
          {'kind':'phase','label':'comp-switch-done','monotonicNs':30},
          {'kind':'phase','label':'comp-switch-back-start','monotonicNs':40},
          {'kind':'candidate-hit','label':'pano-item-activate','monotonicNs':50,'wallTimeNs':200},
          {'kind':'phase','label':'comp-switch-back-done','monotonicNs':60},
        ]
        ev=[
          {'kind':'snapshot-before','phase':'comp-switch','snapshot':{'ok':True,'value':'comp=A'}},
          {'kind':'snapshot-after','phase':'comp-switch','snapshot':{'ok':True,'value':'comp=B'}},
          {'kind':'snapshot-before','phase':'comp-switch-back','snapshot':{'ok':True,'value':'comp=B'}},
          {'kind':'snapshot-after','phase':'comp-switch-back','snapshot':{'ok':True,'value':'comp=A'}},
        ]
        out=c.analyze(trace,ev,{'markers':[]})
        self.assertEqual(out['activeComp'],'OBSERVED')
        self.assertEqual(out['stateOracle'],'OBSERVED')

    def test_marker_source_has_no_unsupported_flush_and_writes_all_markers(self):
        source=(ROOT/'research/ae-notifications/FSTR-PostCommit-Marker.jsx').read_text(encoding='utf-8')
        self.assertNotIn('.flush(',source)
        self.assertIn('before|',source)
        self.assertIn('after-mutation|',source)
        self.assertIn('after-end-undo|',source)
        self.assertIn('out.close()',source)

    def test_script_marker_accepts_return_after_end_undo(self):
        base=1_700_000_000_000
        trace=[
          {'kind':'phase','label':'script-postcommit-start','monotonicNs':1},
          {'kind':'candidate-hit','label':'after-process-from-render-thread','monotonicNs':2,'wallTimeNs':(base+5)*1000000},
          {'kind':'candidate-hit','label':'process-project-changes-return','monotonicNs':3,'wallTimeNs':(base+6)*1000000},
          {'kind':'phase','label':'script-postcommit-done','monotonicNs':4},
        ]
        out=c.analyze(trace,[],{'markers':[{'label':'after-end-undo','wallTimeMs':base}]})
        self.assertEqual(out['postProcessing'],'OBSERVED_AFTER_SCRIPT_END_UNDO')

if __name__=='__main__': unittest.main()
