#!/usr/bin/env python3
"""Strict parser/gate for FSTR Chain Probe JSONL evidence. No AE launch or install."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

MAX_BYTES=1024*1024
MAX_LINES=10000
MAX_EXPECTED_BYTES=64*1024
MAX_EXPECTED_STATES=100
COMMAND_RE=re.compile(r'^COMMAND_READY id=([1-9][0-9]*)$')
OBS_RE=re.compile(
    r'^OBSERVATION_NOT_COMMIT_PROOF generation=(?P<generation>[0-9]+) '
    r'active=(?P<active>[01]) id=(?P<id>-?[0-9]+) '
    r'offset=(?P<offset_value>-?[0-9]+)/(?P<offset_scale>[0-9]+) '
    r'in=(?P<in_value>-?[0-9]+)/(?P<in_scale>[0-9]+) '
    r'duration=(?P<duration_value>-?[0-9]+)/(?P<duration_scale>[0-9]+) '
    r'entered=(?P<entered>[0-9]+) zero=(?P<zero>[0-9]+) '
    r'error=(?P<error>[0-9]+) unwound=(?P<unwound>[0-9]+)$')
FATAL_PREFIXES=(
    'HOST_EXIT_FORWARDING_RETAINED',
    'REMOVE_BLOCKED_FORWARDING_RETAINED',
    'REMOVE_UNCONFIRMED_FORWARDING_RETAINED',
    'REMOVE_EXCEPTION_FORWARDING_RETAINED',
    'INSERT_FAILED_NO_RETRY',
    'INSERT_OUTCOME_UNKNOWN_NO_RETRY',
    'PROBE_MODULE_PIN_FAILED_NO_RETRY',
    'SNAPSHOT_FAILED_PENDING_RETAINED_NO_IDLE_RETRY',
    'SNAPSHOT_EXCEPTION_PENDING_RETAINED',
    'INITIALIZATION_PARTIAL_DISABLED',
)

class EvidenceError(ValueError):
    pass

def parse_trace(path: Path, expected_build_id: str):
    path=Path(path)
    if path.is_symlink() or not path.is_file():
        raise EvidenceError('TRACE_NOT_REGULAR_FILE')
    size=path.stat().st_size
    if size<=0 or size>MAX_BYTES:
        raise EvidenceError('TRACE_SIZE_INVALID')
    rows=[]
    with path.open('r',encoding='utf-8',errors='strict') as handle:
        for number,line in enumerate(handle,1):
            if number>MAX_LINES:
                raise EvidenceError('TRACE_TOO_MANY_LINES')
            if len(line)>4096:
                raise EvidenceError('TRACE_LINE_TOO_LONG')
            try:
                row=json.loads(line)
            except json.JSONDecodeError as error:
                raise EvidenceError(f'TRACE_JSON_INVALID:{number}') from error
            if not isinstance(row,dict) or set(row)!= {'schemaVersion','buildId','sequence','wallTimeNs','event'}:
                raise EvidenceError(f'TRACE_SCHEMA_INVALID:{number}')
            if row['schemaVersion']!=1 or row['buildId']!=expected_build_id:
                raise EvidenceError(f'TRACE_IDENTITY_MISMATCH:{number}')
            if type(row['sequence']) is not int or row['sequence']!=number:
                raise EvidenceError(f'TRACE_SEQUENCE_INVALID:{number}')
            if type(row['wallTimeNs']) is not int or row['wallTimeNs']<=0:
                raise EvidenceError(f'TRACE_TIME_INVALID:{number}')
            if not isinstance(row['event'],str) or not row['event'] or len(row['event'])>511:
                raise EvidenceError(f'TRACE_EVENT_INVALID:{number}')
            rows.append(row)
    return rows

def load_expected_states(path: Path, expected_build_id: str):
    path=Path(path)
    if path.is_symlink() or not path.is_file():
        raise EvidenceError('EXPECTED_STATES_NOT_REGULAR_FILE')
    size=path.stat().st_size
    if size<=0 or size>MAX_EXPECTED_BYTES:
        raise EvidenceError('EXPECTED_STATES_SIZE_INVALID')
    try:
        data=json.loads(path.read_text(encoding='utf-8',errors='strict'))
    except json.JSONDecodeError as error:
        raise EvidenceError('EXPECTED_STATES_JSON_INVALID') from error
    if not isinstance(data,dict) or set(data)!={'schemaVersion','kind','buildId','states'}:
        raise EvidenceError('EXPECTED_STATES_SCHEMA_INVALID')
    if data['schemaVersion']!=1 or data['kind']!='FSTRChainProbeExpectedStates' or data['buildId']!=expected_build_id:
        raise EvidenceError('EXPECTED_STATES_IDENTITY_MISMATCH')
    states=data['states']
    if not isinstance(states,list) or not 2<=len(states)<=MAX_EXPECTED_STATES:
        raise EvidenceError('EXPECTED_STATES_COUNT_INVALID')
    normalized=[]; labels=set()
    for index,state in enumerate(states,1):
        if not isinstance(state,dict) or set(state)!={'label','id','offset','in','duration'}:
            raise EvidenceError(f'EXPECTED_STATE_SCHEMA_INVALID:{index}')
        label=state['label']
        if not isinstance(label,str) or not label or len(label)>80 or '\n' in label or label in labels:
            raise EvidenceError(f'EXPECTED_STATE_LABEL_INVALID:{index}')
        if type(state['id']) is not int or state['id']<=0:
            raise EvidenceError(f'EXPECTED_STATE_ID_INVALID:{index}')
        values={}
        for key in ('offset','in','duration'):
            pair=state[key]
            if not isinstance(pair,list) or len(pair)!=2 or any(type(value) is not int for value in pair) or pair[1]<=0:
                raise EvidenceError(f'EXPECTED_STATE_TIME_INVALID:{index}:{key}')
            values[key]=(pair[0],pair[1])
        if values['duration'][0]<0:
            raise EvidenceError(f'EXPECTED_STATE_TIME_INVALID:{index}:duration')
        labels.add(label)
        normalized.append({'label':label,'id':state['id'],**values})
    return normalized

def _events(rows):
    return [row['event'] for row in rows]

def _command(events):
    ids=[int(m.group(1)) for event in events if (m:=COMMAND_RE.match(event))]
    if len(ids)!=1:
        raise EvidenceError('COMMAND_READY_COUNT_INVALID')
    return ids[0]

def _observation(event):
    if not event.startswith('OBSERVATION_NOT_COMMIT_PROOF'):
        return None
    match=OBS_RE.fullmatch(event)
    if not match:
        raise EvidenceError('OBSERVATION_FORMAT_INVALID')
    values={key:int(value) for key,value in match.groupdict().items()}
    if values['active'] and (values['offset_scale']<=0 or values['in_scale']<=0 or values['duration_scale']<=0):
        raise EvidenceError('OBSERVATION_TIME_SCALE_INVALID')
    return values

def _observations(events):
    observations=[]
    for index,event in enumerate(events):
        observation=_observation(event)
        if observation is not None:
            observations.append((index,observation))
    return observations

def verify_disabled(rows):
    events=_events(rows)
    if not events or events[0]!='LOADED_DISABLED_BUILD_ID_IN_EVENT_TYPE_NO_PROJECT_READS':
        raise EvidenceError('DISABLED_LOAD_MARKER_MISSING')
    command_id=_command(events)
    forbidden=('REGISTERED_RESEARCH_ONLY_SYNC001_NOT_RUN','OBSERVATION_NOT_COMMIT_PROOF','REMOVED_OWN_ID')
    if any(any(event.startswith(prefix) for prefix in forbidden) for event in events):
        raise EvidenceError('DISABLED_PRIVATE_ACTIVITY_OBSERVED')
    if any(any(event.startswith(prefix) for prefix in FATAL_PREFIXES) for event in events):
        raise EvidenceError('FATAL_EVENT_OBSERVED')
    if events[-1] != 'HOST_EXIT_NO_REGISTRATION':
        raise EvidenceError('DISABLED_CLEAN_EXIT_MISSING')
    return {'status':'PASS','mode':'disabled','commandId':command_id,'events':len(events),'AEGP_load':'OBSERVED','SYNC-001':'NOT RUN'}

def verify_active(rows,min_observations=2):
    if min_observations<2:
        raise EvidenceError('MIN_OBSERVATIONS_TOO_SMALL')
    events=_events(rows)
    if not events or events[0]!='LOADED_DISABLED_BUILD_ID_IN_EVENT_TYPE_NO_PROJECT_READS':
        raise EvidenceError('ACTIVE_LOAD_MARKER_MISSING')
    command_id=_command(events)
    if any(any(event.startswith(prefix) for prefix in FATAL_PREFIXES) for event in events):
        raise EvidenceError('FATAL_EVENT_OBSERVED')
    registrations=[i for i,e in enumerate(events) if e=='REGISTERED_RESEARCH_ONLY_SYNC001_NOT_RUN']
    removals=[i for i,e in enumerate(events) if e=='REMOVED_OWN_ID']
    if len(registrations)!=1:
        raise EvidenceError('REGISTRATION_COUNT_INVALID')
    if len(removals)!=1 or removals[0]<=registrations[0]:
        raise EvidenceError('REMOVAL_ORDER_INVALID')
    observations=_observations(events)
    if len(observations)<min_observations:
        raise EvidenceError('OBSERVATION_COUNT_INSUFFICIENT')
    if observations[0][0]<=registrations[0] or observations[-1][0]>=removals[0]:
        raise EvidenceError('OBSERVATION_ORDER_INVALID')
    generations=[value['generation'] for _,value in observations]
    if any(b<=a for a,b in zip(generations,generations[1:])):
        raise EvidenceError('OBSERVATION_GENERATION_NOT_INCREASING')
    if events[-1]!='HOST_EXIT_NO_REGISTRATION':
        raise EvidenceError('ACTIVE_CLEAN_EXIT_MISSING')
    return {'status':'PASS','mode':'active','commandId':command_id,'observations':len(observations),
            'firstGeneration':generations[0],'lastGeneration':generations[-1],
            'AEGP_load':'OBSERVED','SYNC-001':'PARTIAL_RUNTIME_EVIDENCE_ONLY'}

def verify_expected_states(rows,expected_states):
    result=verify_active(rows,len(expected_states))
    actual=[value for _,value in _observations(_events(rows))]
    if len(actual)!=len(expected_states):
        raise EvidenceError('EXPECTED_STATE_OBSERVATION_COUNT_MISMATCH')
    for index,(observed,expected) in enumerate(zip(actual,expected_states),1):
        actual_state={
            'id':observed['id'],
            'offset':(observed['offset_value'],observed['offset_scale']),
            'in':(observed['in_value'],observed['in_scale']),
            'duration':(observed['duration_value'],observed['duration_scale']),
        }
        if observed['active']!=1 or actual_state!={key:expected[key] for key in ('id','offset','in','duration')}:
            raise EvidenceError(f'EXPECTED_STATE_MISMATCH:{index}:{expected["label"]}')
    result.update({'stateSequence':'OBSERVED','expectedStateCount':len(expected_states),
                   'stateLabels':[state['label'] for state in expected_states]})
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace',type=Path,required=True)
    parser.add_argument('--build-id',required=True)
    parser.add_argument('--mode',choices=('disabled','active'),required=True)
    parser.add_argument('--min-observations',type=int,default=2)
    parser.add_argument('--expected-states',type=Path,
                        help='strict build-bound expected active-layer state sequence; active mode only')
    args=parser.parse_args()
    try:
        rows=parse_trace(args.trace,args.build_id)
        if args.mode=='disabled':
            if args.expected_states:
                raise EvidenceError('EXPECTED_STATES_REQUIRE_ACTIVE_MODE')
            result=verify_disabled(rows)
        elif args.expected_states:
            states=load_expected_states(args.expected_states,args.build_id)
            result=verify_expected_states(rows,states)
        else:
            result=verify_active(rows,args.min_observations)
    except (OSError,UnicodeError,EvidenceError) as error:
        raise SystemExit('FAIL: '+str(error))
    print(json.dumps(result,sort_keys=True))
if __name__=='__main__':
    main()
