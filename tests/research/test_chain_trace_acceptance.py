import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MODULE=ROOT/'research/ae-notifications/chain-probe/trace_acceptance.py'
spec=importlib.util.spec_from_file_location('fstr_chain_trace_acceptance',MODULE)
trace=importlib.util.module_from_spec(spec); spec.loader.exec_module(trace)

BUILD='fstr-chain-aegp-test-research-opt-in'

def rows(events):
    return [{'schemaVersion':1,'buildId':BUILD,'sequence':i+1,'wallTimeNs':1000+i,'event':event}
            for i,event in enumerate(events)]

def write_trace(events,mutate=None):
    temp=tempfile.TemporaryDirectory()
    path=Path(temp.name)/'trace.jsonl'
    data=rows(events)
    if mutate: mutate(data)
    path.write_text(''.join(json.dumps(row,separators=(',',':'))+'\n' for row in data),encoding='utf-8')
    return temp,path

def expected_states():
    return [
        {'label':'edit-1','id':12,'offset':(2,24),'in':(3,24),'duration':(60,24)},
        {'label':'edit-2','id':12,'offset':(4,24),'in':(5,24),'duration':(60,24)},
    ]

DISABLED=[
    'LOADED_DISABLED_BUILD_ID_IN_EVENT_TYPE_NO_PROJECT_READS',
    'COMMAND_READY id=77',
    'HOST_EXIT_NO_REGISTRATION',
]
ACTIVE=[
    'LOADED_DISABLED_BUILD_ID_IN_EVENT_TYPE_NO_PROJECT_READS',
    'COMMAND_READY id=77',
    'REGISTERED_RESEARCH_ONLY_SYNC001_NOT_RUN',
    'OBSERVATION_NOT_COMMIT_PROOF generation=2 active=1 id=12 offset=2/24 in=3/24 duration=60/24 entered=2 zero=2 error=0 unwound=0',
    'OBSERVATION_NOT_COMMIT_PROOF generation=3 active=1 id=12 offset=4/24 in=5/24 duration=60/24 entered=3 zero=3 error=0 unwound=0',
    'REMOVED_OWN_ID',
    'HOST_EXIT_NO_REGISTRATION',
]

class TraceAcceptanceTests(unittest.TestCase):
    def parse(self,events,mutate=None):
        temp,path=write_trace(events,mutate)
        self.addCleanup(temp.cleanup)
        return trace.parse_trace(path,BUILD)

    def test_disabled_pass(self):
        result=trace.verify_disabled(self.parse(DISABLED))
        self.assertEqual((result['status'],result['commandId']),('PASS',77))

    def test_observation_regex_matches_full_state(self):
        match=trace.OBS_RE.match(ACTIVE[3])
        self.assertIsNotNone(match)
        self.assertEqual((match.group('generation'),match.group('id'),match.group('offset_value')),('2','12','2'))

    def test_active_pass_requires_two_ordered_observations_and_stop(self):
        result=trace.verify_active(self.parse(ACTIVE))
        self.assertEqual(result['observations'],2)
        self.assertEqual((result['firstGeneration'],result['lastGeneration']),(2,3))

    def test_expected_states_match_exact_active_sequence(self):
        result=trace.verify_expected_states(self.parse(ACTIVE),expected_states())
        self.assertEqual(result['stateSequence'],'OBSERVED')
        self.assertEqual(result['stateLabels'],['edit-1','edit-2'])

    def test_expected_states_reject_state_mismatch(self):
        expected=expected_states(); expected[1]={**expected[1],'offset':(99,24)}
        with self.assertRaisesRegex(trace.EvidenceError,'EXPECTED_STATE_MISMATCH:2:edit-2'):
            trace.verify_expected_states(self.parse(ACTIVE),expected)

    def test_expected_states_reject_extra_stable_observation(self):
        extra='OBSERVATION_NOT_COMMIT_PROOF generation=4 active=1 id=12 offset=4/24 in=5/24 duration=60/24 entered=4 zero=4 error=0 unwound=0'
        bad=ACTIVE[:-2]+[extra]+ACTIVE[-2:]
        with self.assertRaisesRegex(trace.EvidenceError,'OBSERVATION_COUNT_MISMATCH'):
            trace.verify_expected_states(self.parse(bad),expected_states())

    def test_active_rejects_snapshot_read_failure(self):
        bad=ACTIVE[:4]+['SNAPSHOT_FAILED_PENDING_RETAINED_NO_IDLE_RETRY']+ACTIVE[4:]
        with self.assertRaisesRegex(trace.EvidenceError,'FATAL_EVENT'):
            trace.verify_active(self.parse(bad))

    def test_active_rejects_malformed_observation(self):
        bad=ACTIVE.copy(); bad[3]=bad[3].replace(' offset=2/24','')
        with self.assertRaisesRegex(trace.EvidenceError,'OBSERVATION_FORMAT_INVALID'):
            trace.verify_active(self.parse(bad))

    def test_disabled_rejects_registration(self):
        bad=DISABLED[:-1]+['REGISTERED_RESEARCH_ONLY_SYNC001_NOT_RUN',DISABLED[-1]]
        with self.assertRaisesRegex(trace.EvidenceError,'DISABLED_PRIVATE_ACTIVITY'):
            trace.verify_disabled(self.parse(bad))

    def test_active_rejects_missing_stop(self):
        bad=[e for e in ACTIVE if e!='REMOVED_OWN_ID']
        with self.assertRaisesRegex(trace.EvidenceError,'REMOVAL_ORDER'):
            trace.verify_active(self.parse(bad))

    def test_active_rejects_retained_forwarder(self):
        bad=ACTIVE[:-1]+['HOST_EXIT_FORWARDING_RETAINED']
        with self.assertRaisesRegex(trace.EvidenceError,'FATAL_EVENT'):
            trace.verify_active(self.parse(bad))

    def test_active_rejects_nonincreasing_generation(self):
        bad=ACTIVE.copy()
        bad[4]=bad[4].replace('generation=3','generation=2')
        with self.assertRaisesRegex(trace.EvidenceError,'GENERATION_NOT_INCREASING'):
            trace.verify_active(self.parse(bad))

    def test_parser_rejects_sequence_gap(self):
        with self.assertRaisesRegex(trace.EvidenceError,'SEQUENCE_INVALID'):
            self.parse(DISABLED,lambda data:data[1].__setitem__('sequence',9))

    def test_parser_rejects_build_mismatch(self):
        temp,path=write_trace(DISABLED)
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(trace.EvidenceError,'IDENTITY_MISMATCH'):
            trace.parse_trace(path,'other-build')

    def test_parser_rejects_non_object_json(self):
        temp=tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        path=Path(temp.name)/'trace.jsonl'
        path.write_text('[]\n',encoding='utf-8')
        with self.assertRaisesRegex(trace.EvidenceError,'SCHEMA_INVALID'):
            trace.parse_trace(path,BUILD)

    def test_active_refuses_less_than_two_observations(self):
        with self.assertRaisesRegex(trace.EvidenceError,'MIN_OBSERVATIONS_TOO_SMALL'):
            trace.verify_active(self.parse(ACTIVE),1)

    def test_parser_rejects_extra_schema_field(self):
        with self.assertRaisesRegex(trace.EvidenceError,'SCHEMA_INVALID'):
            self.parse(DISABLED,lambda data:data[0].__setitem__('extra',1))

    def test_expected_state_file_is_build_bound_and_strict(self):
        temp=tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        path=Path(temp.name)/'states.json'
        data={'schemaVersion':1,'kind':'FSTRChainProbeExpectedStates','buildId':BUILD,
              'states':[{'label':state['label'],'id':state['id'],'offset':list(state['offset']),
                         'in':list(state['in']),'duration':list(state['duration'])}
                        for state in expected_states()]}
        path.write_text(json.dumps(data),encoding='utf-8')
        loaded=trace.load_expected_states(path,BUILD)
        self.assertEqual(loaded,expected_states())
        with self.assertRaisesRegex(trace.EvidenceError,'IDENTITY_MISMATCH'):
            trace.load_expected_states(path,'other-build')

if __name__=='__main__':
    unittest.main()
