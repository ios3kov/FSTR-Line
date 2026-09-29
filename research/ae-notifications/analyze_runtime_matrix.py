#!/usr/bin/env python3
"""Offline analyzer for FSTR Final Matrix ZIP evidence. No AE access."""
from __future__ import annotations
import argparse, hashlib, json, zipfile
from collections import Counter
from pathlib import Path

KNOWN_MARKERS=(
    "render-end-undo-group","end-group","set-content-changed",
    "undo-command","redo-command","layer-switch-internal",
    "select-layer","layerselection-set","cmd-seek-item-to-time",
)

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def rows_from_bytes(data):
    rows=[]
    for raw in data.decode("utf-8","replace").splitlines():
        if raw.strip():
            row=json.loads(raw)
            if not isinstance(row,dict):
                raise ValueError("JSONL row must be object")
            rows.append(row)
    return rows

def phase_windows(rows):
    starts={}
    windows={}
    for row in rows:
        if row.get("kind")!="phase":
            continue
        label=row.get("label","")
        if label.endswith("-start"):
            starts[label[:-6]]=row
        elif label.endswith("-done"):
            name=label[:-5]
            if name in starts:
                windows[name]=(starts[name]["monotonicNs"],row["monotonicNs"])
    return windows

def analyze_session(rows):
    windows=phase_windows(rows)
    hits=[r for r in rows if r.get("kind")=="candidate-hit"]
    out={"hits":len(hits),"windows":{}}
    for name,(start,end) in windows.items():
        wh=[h for h in hits if start<=h.get("monotonicNs",0)<=end]
        counts=Counter(h.get("label") for h in wh)
        pjc=[h for h in wh if h.get("label")=="process-project-changes"]
        later=[]
        if pjc:
            last_p=max(h["monotonicNs"] for h in pjc)
            for marker in KNOWN_MARKERS:
                ts=[h["monotonicNs"] for h in wh if h.get("label")==marker]
                if ts and max(ts)>last_p:
                    later.append({"label":marker,"afterLastProcessMs":round((max(ts)-last_p)/1e6,3)})
        out["windows"][name]={
            "durationMs":round((end-start)/1e6,3),
            "hits":len(wh),
            "counts":dict(sorted(counts.items())),
            "lastProcessProjectChangesAfterKnownMarkers":bool(pjc) and not later,
            "knownMarkersAfterLastProcessProjectChanges":later,
        }
    return out

def analyze(path):
    path=Path(path)
    digest=sha256(path)
    with zipfile.ZipFile(path) as z:
        names=set(z.namelist())
        required={"summary.json","evidence.jsonl","pre-restart/trace.jsonl",
                  "pre-restart/result.json","post-restart/trace.jsonl","post-restart/result.json"}
        missing=sorted(required-names)
        if missing:
            raise ValueError("Missing Final Matrix entries: "+", ".join(missing))
        summary=json.loads(z.read("summary.json"))
        evidence=rows_from_bytes(z.read("evidence.jsonl"))
        sessions={}
        for session in ("pre-restart","post-restart"):
            trace=rows_from_bytes(z.read(session+"/trace.jsonl"))
            result=json.loads(z.read(session+"/result.json"))
            sessions[session]={"runtimeResult":result,**analyze_session(trace)}
    restart=next((r for r in evidence if r.get("kind")=="restart-observed"),None)
    snapshots=[r for r in evidence if r.get("kind") in ("snapshot-before","snapshot-after")]
    snapshot_values=[r.get("snapshot",{}).get("value") for r in snapshots if r.get("snapshot",{}).get("ok")]
    snapshot_oracle_valid=bool(snapshot_values) and any(v not in (None,"","0") for v in snapshot_values)
    plugin_window=sessions["pre-restart"]["windows"].get("other-plugin-origin",{})
    active_comp=sessions["pre-restart"]["windows"].get("native-comp-switch",{})
    idle_names=("idle-control","idle-before-restart","restart-idle","restart-idle-after")
    idle_hits=0
    for name in idle_names:
        for s in sessions.values():
            if name in s["windows"]:
                idle_hits+=s["windows"][name]["hits"]
    script_windows=[
        sessions["pre-restart"]["windows"].get("extendscript-origin",{}),
        sessions["post-restart"]["windows"].get("restart-extendscript",{}),
    ]
    report={
        "schemaVersion":1,
        "kind":"final-matrix-analysis",
        "inputSha256":digest,
        "inputBuild":summary.get("collectorBuild",{}),
        "runtimeStatus":summary.get("status"),
        "sessions":sessions,
        "observations":{
            "idleCandidateHits":idle_hits,
            "nativeCompSwitchProcessProjectChanges":
                active_comp.get("counts",{}).get("process-project-changes",0),
            "extendScriptProcessProjectChanges":
                [w.get("counts",{}).get("process-project-changes",0) for w in script_windows],
            "otherPluginWindowProcessProjectChanges":
                plugin_window.get("counts",{}).get("process-project-changes",0),
            "restartPidChanged":restart.get("pidChanged") if restart else None,
            "snapshotOracleValid":snapshot_oracle_valid,
        },
        "gates":{
            "commonNativePath":"OBSERVED",
            "extendScriptOrigin":"OBSERVED" if all(x>0 for x in [
                w.get("counts",{}).get("process-project-changes",0) for w in script_windows]) else "UNPROVEN",
            "activeCompSwitch":"GAP" if active_comp.get("hits",0)==0 else "OBSERVED",
            "otherPluginOrigin":"UNPROVEN",
            "postCommitSemantics":"UNPROVEN" if not snapshot_oracle_valid else "PARTIAL",
            "restartReopen":"OBSERVED" if restart and restart.get("pidChanged") else "UNPROVEN",
            "SYNC-001":"NOT RUN",
        },
        "limitations":[
            "Window correlation is not proof that a private function is a supported notification API.",
            "A process-project-changes hit may occur more than once per user action.",
            "Other-plugin provenance cannot be inferred from a generic action window alone.",
            "Post-commit remains unproven when the state oracle is invalid or later markers follow a hit.",
        ],
    }
    return report

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("matrix",type=Path)
    p.add_argument("--output",type=Path)
    args=p.parse_args(argv)
    report=analyze(args.matrix)
    text=json.dumps(report,indent=2,ensure_ascii=False)+"\n"
    if args.output:
        args.output.write_text(text,encoding="utf-8")
    else:
        print(text,end="")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
