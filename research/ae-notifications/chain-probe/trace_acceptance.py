#!/usr/bin/env python3
"""Strict parser/gate for FSTR Chain Probe JSONL evidence. No AE launch or install."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

MAX_BYTES=1024*1024
MAX_LINES=10000
COMMAND_RE=re.compile(r'^COMMAND_READY id=([1-9][0-9]*)$')
OBS_RE=re.compile(r'^OBSERVATION_NOT_COMMIT_PROOF generation=([0-9]+)\b')
FATAL_PREFIXES=(
    'HOST_EXIT_FORWARDING_RETAINED',
    'REMOVE_BLOCKED_FORWARDING_RETAINED',
    'REMOVE_UNCONFIRMED_FORWARDING_RETAINED',
    'REMOVE_EXCEPTION_FORWARDING_RETAINED',
    'INSERT_FAILED_NO_RETRY',
    'INSERT_OUTCOME_UNKNOWN_NO_RETRY',
    'PROBE_MODULE_PIN_FAILED_NO_RETRY',
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

def _events(rows):
    return [row['event'] for row in rows]

def _command(events):
    ids=[int(m.group(1)) for event in events if (m:=COMMAND_RE.match(event))]
    if len(ids)!=1:
        raise EvidenceError('COMMAND_READY_COUNT_INVALID')
    return ids[0]

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
    observations=[]
    for i,event in enumerate(events):
        match=OBS_RE.match(event)
        if match:
            observations.append((i,int(match.group(1))))
    if len(observations)<min_observations:
        raise EvidenceError('OBSERVATION_COUNT_INSUFFICIENT')
    if observations[0][0]<=registrations[0] or observations[-1][0]>=removals[0]:
        raise EvidenceError('OBSERVATION_ORDER_INVALID')
    generations=[value for _,value in observations]
    if any(b<=a for a,b in zip(generations,generations[1:])):
        raise EvidenceError('OBSERVATION_GENERATION_NOT_INCREASING')
    if events[-1]!='HOST_EXIT_NO_REGISTRATION':
        raise EvidenceError('ACTIVE_CLEAN_EXIT_MISSING')
    return {'status':'PASS','mode':'active','commandId':command_id,'observations':len(observations),
            'firstGeneration':generations[0],'lastGeneration':generations[-1],
            'AEGP_load':'OBSERVED','SYNC-001':'PARTIAL_RUNTIME_EVIDENCE_ONLY'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace',type=Path,required=True)
    parser.add_argument('--build-id',required=True)
    parser.add_argument('--mode',choices=('disabled','active'),required=True)
    parser.add_argument('--min-observations',type=int,default=2)
    args=parser.parse_args()
    try:
        rows=parse_trace(args.trace,args.build_id)
        result=verify_disabled(rows) if args.mode=='disabled' else verify_active(rows,args.min_observations)
    except (OSError,UnicodeError,EvidenceError) as error:
        raise SystemExit('FAIL: '+str(error))
    print(json.dumps(result,sort_keys=True))
if __name__=='__main__':
    main()
