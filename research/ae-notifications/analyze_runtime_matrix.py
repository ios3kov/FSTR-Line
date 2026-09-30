#!/usr/bin/env python3
"""Offline analyzer for FSTR Final Matrix ZIP evidence. No AE access."""
from __future__ import annotations
import argparse, hashlib, json, re, stat, zipfile
from collections import Counter
from pathlib import Path, PurePosixPath

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

def _unique_fields(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("Duplicate JSON field: " + key)
        out[key] = value
    return out


def json_object(data):
    value = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_fields)
    if not isinstance(value, dict):
        raise ValueError("JSON record must be an object")
    return value


def rows_from_bytes(data):
    if data.strip() and not data.endswith(b"\n"):
        raise ValueError("Incomplete JSONL stream")
    rows=[]
    for raw in data.decode("utf-8").splitlines():
        if raw.strip():
            row=json_object(raw.encode("utf-8"))
            rows.append(row)
            if len(rows) > MAX_JSONL_ROWS:
                raise ValueError("JSONL row limit exceeded")
    return rows

def phase_windows(rows):
    starts={}
    windows={}
    for row in rows:
        if row.get("kind")!="phase":
            continue
        label=row.get("label","")
        if not isinstance(label, str):
            raise ValueError("Invalid phase label")
        if label.endswith("-start"):
            starts[label[:-6]]=row
        elif label.endswith("-done"):
            name=label[:-5]
            if name in starts:
                windows[name]=(starts[name]["monotonicNs"],row["monotonicNs"])
                if len(windows) > MAX_WINDOWS:
                    raise ValueError("Phase window limit exceeded")
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

# Bounds apply before allocation; ZIP inputs are never extracted or executed.
MAX_JSONL_ROWS = 12000
MAX_WINDOWS = 128
MAX_MEMBERS = 64
MAX_MEMBER_BYTES = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024
NORMAL_SESSIONS = ("pre-restart", "post-restart")
RESUMED_SESSIONS = ("pre-restart-partial", "pre-restart-resume", "post-restart")


def _members(archive):
    entries = archive.infolist()
    if len(entries) > MAX_MEMBERS:
        raise ValueError("Matrix member limit exceeded")
    names = set()
    total = 0
    for entry in entries:
        parts = PurePosixPath(entry.filename).parts
        if (entry.filename in names or not parts or entry.filename.startswith("/")
                or ".." in parts or "\\" in entry.filename
                or stat.S_ISLNK(entry.external_attr >> 16)):
            raise ValueError("Unsafe or duplicate matrix member")
        if entry.file_size > MAX_MEMBER_BYTES or entry.flag_bits & 1:
            raise ValueError("Oversized or encrypted matrix member")
        total += entry.file_size
        names.add(entry.filename)
    if total > MAX_TOTAL_BYTES:
        raise ValueError("Matrix byte limit exceeded")
    return names


def _read(archive, name):
    # A second bound covers actual output rather than only central-directory metadata.
    with archive.open(name) as stream:
        data = stream.read(MAX_MEMBER_BYTES + 1)
    if len(data) > MAX_MEMBER_BYTES:
        raise ValueError("Matrix member output limit exceeded")
    return data


def observer_integrity(trace, result, result_bytes, parent, *, partial=False):
    """Validate supplied lifecycle records, not authenticity, ABI or delivery."""
    reasons = []
    wanted_status, wanted_stage = ("BLOCKED", "aborted") if partial else ("PASS", "complete")
    pid = result.get("pid")
    if (result.get("status") != wanted_status or result.get("stage") != wanted_stage
            or result.get("detached") is not True or type(pid) is not int or pid <= 0):
        reasons.append("CONTROLLER_NOT_COMPLETE_OR_DETACHED")
    if not parent:
        reasons.append("PARENT_RECORD_MISSING")
    else:
        if (parent.get("schemaVersion") != 1 or parent.get("kind") != "observer-parent-exit"
                or parent.get("status") != wanted_status
                or parent.get("debuggerReaped") is not True
                or type(parent.get("debuggerExitCode")) is not int
                or parent["debuggerExitCode"] != 0
                or parent.get("shutdownTimedOut") is not False
                or parent.get("forcedTermination") is not False
                or parent.get("cleanupErrors") != []
                or parent.get("resumeEligible") is not partial):
            reasons.append("ABNORMAL_PARENT_EXIT")
        if (parent.get("controllerResultSha256") != hashlib.sha256(result_bytes).hexdigest()
                or parent.get("controllerStatus") != wanted_status
                or parent.get("controllerDetached") is not True):
            reasons.append("PARENT_RESULT_BINDING_MISMATCH")
        if partial:
            if parent.get("sessionError") not in ("KeyboardInterrupt", "EOFError"):
                reasons.append("PARTIAL_NOT_CLEAN_USER_ABORT")
        elif "sessionError" in parent:
            reasons.append("PARENT_SESSION_ERROR")
        if any(key in parent for key in ("abortError", "resultError")):
            reasons.append("PARENT_DIAGNOSTIC_ERROR")
    run_id = parent.get("runId")
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", run_id):
        reasons.append("RUN_ID_MISSING")
    if (len(trace) < 4 or trace[0].get("kind") != "capture-start"
            or trace[-1].get("kind") != "capture-end"):
        reasons.append("TRACE_INCOMPLETE")
    else:
        kinds = [row.get("kind") for row in trace]
        hits = [row for row in trace if row.get("kind") == "candidate-hit"]
        if (kinds.count("capture-start") != 1 or kinds.count("capture-end") != 1
                or any(not isinstance(kind, str) for kind in kinds)
                or set(kinds) - {"capture-start", "capture-end", "candidate-hit", "phase"}
                or type(trace[-1].get("hits")) is not int or trace[-1]["hits"] != len(hits)):
            reasons.append("TRACE_ERROR_OR_COUNT_MISMATCH")
        previous = -1
        active = None
        completed = set()
        labels = []
        for index, row in enumerate(trace, 1):
            stamp = row.get("monotonicNs")
            if (row.get("testRunId") != run_id or type(row.get("sequence")) is not int
                    or row["sequence"] != index or type(stamp) is not int or stamp < 0 or stamp < previous):
                reasons.append("TRACE_ID_SEQUENCE_OR_TIME_MISMATCH")
                break
            previous = stamp
            kind = row.get("kind")
            if kind == "candidate-hit" and (type(row.get("pid")) is not int or row["pid"] != pid
                    or row.get("isNotificationProven") is not False
                    or row.get("commitPhase") != "UNKNOWN" or row.get("source") != "lldb-breakpoint"
                    or not isinstance(row.get("label"), str)):
                reasons.append("TRACE_HIT_IDENTITY_OR_CLAIM_MISMATCH")
            if kind == "phase":
                label = row.get("label")
                if not isinstance(label, str):
                    reasons.append("INVALID_PHASE_LABEL")
                    continue
                labels.append(label)
                if label.endswith("-start"):
                    if active is not None or label[:-6] in completed:
                        reasons.append("AMBIGUOUS_PHASE_WINDOW")
                    active = label[:-6]
                elif label.endswith("-done"):
                    if active != label[:-5] or active in completed:
                        reasons.append("AMBIGUOUS_PHASE_WINDOW")
                    completed.add(label[:-5])
                    active = None
        ending = "capture-aborted" if partial else "capture-finished"
        if (labels.count("attach-verified") != 1 or labels.count(ending) != 1
                or not labels or labels[0] != "attach-verified" or labels[-1] != ending
                or (active is not None and not partial)):
            reasons.append("TRACE_LIFECYCLE_MARKERS_MISMATCH")
    return {"status": "BLOCKED" if reasons else "PASS", "reasons": sorted(set(reasons)),
            "runId": run_id, "partial": partial,
            "scope": "supplied observer lifecycle records, not notification delivery"}


def _record_ok(value):
    return (isinstance(value, dict) and value.get("ok") is True
            and value.get("timedOut") is False
            and type(value.get("returnCode")) is int and value["returnCode"] == 0)


def analyze(path):
    path = Path(path)
    digest = sha256(path)
    with zipfile.ZipFile(path) as z:
        names = _members(z)
        summary = json_object(_read(z, "summary.json"))
        evidence = rows_from_bytes(_read(z, "evidence.jsonl"))
        layout = summary.get("sessions", list(NORMAL_SESSIONS))
        if not isinstance(layout, list) or tuple(layout) not in (NORMAL_SESSIONS, RESUMED_SESSIONS):
            raise ValueError("Unsupported or ambiguous session layout")
        sessions = {}
        for session in layout:
            required = {session + "/trace.jsonl", session + "/result.json"}
            if not required <= names:
                raise ValueError("Missing Final Matrix entries for " + session)
            trace = rows_from_bytes(_read(z, session + "/trace.jsonl"))
            raw = _read(z, session + "/result.json")
            result = json_object(raw)
            parent_name = session + "/observer-parent.json"
            parent = json_object(_read(z, parent_name)) if parent_name in names else {}
            integrity = observer_integrity(trace, result, raw, parent,
                                           partial=session == "pre-restart-partial")
            try:
                observations = analyze_session(trace)
            except (TypeError, ValueError, KeyError):
                integrity["status"] = "BLOCKED"
                integrity["reasons"].append("INVALID_RAW_WINDOW")
                observations = {"hits": sum(r.get("kind") == "candidate-hit" for r in trace), "windows": {}}
            sessions[session] = {"runtimeResult": result, "observerIntegrity": integrity, **observations}
    integrity_reasons = []
    run_ids = [s["observerIntegrity"]["runId"] for s in sessions.values()]
    if any(not isinstance(run, str) for run in run_ids) or len(set(str(r) for r in run_ids)) != len(run_ids):
        integrity_reasons.append("MISSING_OR_REUSED_SESSION_ID")
    pre = {}
    window_session = {}
    for name in layout[:-1]:
        for phase, window in sessions[name]["windows"].items():
            if phase in pre:
                integrity_reasons.append("DUPLICATE_RESUMED_PHASE")
            pre[phase] = window
            window_session[phase] = "pre-restart" if name == "pre-restart-partial" else name
    if tuple(layout) == RESUMED_SESSIONS and (sessions[layout[0]]["runtimeResult"].get("pid")
                                             != sessions[layout[1]]["runtimeResult"].get("pid")):
        integrity_reasons.append("RESUMED_PID_MISMATCH")
    accepted = (summary.get("status") == "PASS" and not integrity_reasons
                and all(s["observerIntegrity"]["status"] == "PASS" for s in sessions.values()))
    restart_rows = [r for r in evidence if r.get("kind") == "restart-observed"]
    restart = restart_rows[0] if len(restart_rows) == 1 else {}
    old_pid = sessions[layout[0]]["runtimeResult"].get("pid")
    new_pid = sessions["post-restart"]["runtimeResult"].get("pid")
    restart_matches = (type(restart.get("oldPid")) is int and type(restart.get("newPid")) is int
                       and restart["oldPid"] == old_pid and restart["newPid"] == new_pid
                       and old_pid != new_pid and restart.get("pidChanged") is True)
    snapshots = [r for r in evidence if r.get("kind") in ("snapshot-before", "snapshot-after")]
    def usable_shot(row):
        shot = row.get("snapshot")
        return (isinstance(shot, dict) and shot.get("ok") is True and isinstance(shot.get("value"), str)
                and shot["value"] not in ("", "0") and shot.get("timedOut") is not True)
    oracle = any(usable_shot(row) for row in snapshots)  # Raw availability, not a post-commit oracle.
    active = pre.get("native-comp-switch", {})
    plugin = pre.get("other-plugin-origin", {})
    script_locations = [(window_session.get("extendscript-origin"), "extendscript-origin"),
                        ("post-restart", "restart-extendscript")]
    script_windows = [pre.get("extendscript-origin", {}),
                      sessions["post-restart"]["windows"].get("restart-extendscript", {})]
    def script_ok(location):
        matches = [r for r in evidence if r.get("kind") == "script-result"
                   and (r.get("session"), r.get("phase")) == location]
        blocked = any(r.get("kind") == "step-blocked" and
                      (r.get("session"), r.get("phase")) == location for r in evidence)
        return not blocked and len(matches) == 1 and _record_ok(matches[0].get("result"))
    script_observed = (all(script_ok(loc) for loc in script_locations)
                       and all(w.get("counts", {}).get("process-project-changes", 0) > 0 for w in script_windows))
    native_observed = any(name.startswith("native-") and w.get("counts", {}).get("process-project-changes", 0) > 0
                          for name, w in pre.items())
    gates = {name: "UNPROVEN" for name in ("commonNativePath", "extendScriptOrigin", "activeCompSwitch",
             "otherPluginOrigin", "postCommitSemantics", "restartReopen", "restartProcess")}
    gates["SYNC-001"] = "NOT RUN"
    if accepted:
        gates["commonNativePath"] = "OBSERVED" if native_observed else "UNPROVEN"
        gates["extendScriptOrigin"] = "OBSERVED" if script_observed else "UNPROVEN"
        gates["restartProcess"] = "OBSERVED" if restart_matches else "UNPROVEN"
    idle_names = ("idle-control", "idle-before-restart", "restart-idle", "restart-idle-after")
    return {
        "schemaVersion": 2, "kind": "final-matrix-analysis", "inputSha256": digest,
        "inputBuild": summary.get("collectorBuild", {}), "reportedRuntimeStatus": summary.get("status"),
        "runtimeStatus": "PASS" if accepted else "BLOCKED", "sessions": sessions,
        "observerIntegrityReasons": sorted(set(integrity_reasons)),
        "observations": {
            "idleCandidateHits": sum(s["windows"].get(name, {}).get("hits", 0)
                                     for name in idle_names for s in sessions.values()),
            "nativeCompSwitchProcessProjectChanges": active.get("counts", {}).get("process-project-changes", 0),
            "extendScriptProcessProjectChanges": [w.get("counts", {}).get("process-project-changes", 0) for w in script_windows],
            "otherPluginWindowProcessProjectChanges": plugin.get("counts", {}).get("process-project-changes", 0),
            "restartPidChanged": restart.get("pidChanged"), "snapshotOracleValid": oracle,
        }, "gates": gates,
        "limitations": [
            "runtimeStatus validates supplied observer lifecycle evidence only, not full matrix coverage or product acceptance.",
            "Missing legacy parent evidence stays BLOCKED; raw candidate counts are retained, not erased or promoted.",
            "Internal consistency and result hashes do not authenticate the host, source build, or supplied trace.",
            "The original plan is not in current archives; planSha256 cannot be independently recomputed here.",
            "OBSERVED denotes correlation in validated research windows, not complete origin coverage or reliable delivery.",
            "A PID change proves neither the reopened project identity nor post-commit state; those gates remain UNPROVEN.",
            "Snapshot availability and absence of later markers cannot prove post-commit semantics.",
            "Active-comp state identity is not independently validated here; missing windows are not a proven GAP.",
        ],
    }

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
    return 0 if report["runtimeStatus"] == "PASS" else 2

if __name__=="__main__":
    raise SystemExit(main())
