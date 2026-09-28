#!/usr/bin/env python3
"""Focused read-only static corroboration for candidates from an already collected AE report."""
from __future__ import annotations
import argparse, hashlib, json, os, re, selectors, subprocess, sys, time, uuid, zipfile
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import collect_app

MAX_TEXT=16*1024*1024
MAX_NM_INPUT=256*1024*1024
MAX_NM_LINE=1024*1024
MAX_NM_HITS=2000

def run_text(args,timeout=45):
    result=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
    text=(result.stdout or "")+(result.stderr or "")
    if len(text.encode("utf-8","replace"))>MAX_TEXT:
        raise ValueError("Tool output exceeded bounded limit")
    return result.returncode,collect_app.redact(text)

def _stop_owned(proc):
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=2)

def stream_filtered(args,regex,timeout=90,max_input=MAX_NM_INPUT,max_hits=MAX_NM_HITS):
    """Read a subprocess incrementally; retain only matching lines.

    The hard byte cap applies to bytes read from the owned process, not retained
    output. On timeout/cap/oversized line only this child is terminated.
    """
    proc=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if proc.stdout is None:
        raise RuntimeError("Subprocess pipe unavailable")
    selector=selectors.DefaultSelector()
    selector.register(proc.stdout,selectors.EVENT_READ)
    deadline=time.monotonic()+timeout
    total=0
    buffer=b""
    hits=[]
    limited=False
    tail=b""
    try:
        while True:
            remaining=deadline-time.monotonic()
            if remaining<=0:
                _stop_owned(proc)
                raise subprocess.TimeoutExpired(args,timeout)
            events=selector.select(min(0.25,remaining))
            if not events:
                if proc.poll() is not None:
                    chunk=os.read(proc.stdout.fileno(),65536)
                    if not chunk:
                        break
                else:
                    continue
            else:
                chunk=os.read(proc.stdout.fileno(),65536)
                if not chunk:
                    if proc.poll() is not None:
                        break
                    continue
            total+=len(chunk)
            if total>max_input:
                _stop_owned(proc)
                raise ValueError("Tool input exceeded hard byte limit")
            tail=(tail+chunk)[-16384:]
            buffer+=chunk
            if len(buffer)>MAX_NM_LINE and b"\n" not in buffer:
                _stop_owned(proc)
                raise ValueError("Tool produced an oversized line")
            while b"\n" in buffer:
                raw,buffer=buffer.split(b"\n",1)
                line=raw.decode("utf-8","replace")
                if regex.search(line):
                    if len(hits)<max_hits:
                        hits.append(collect_app.redact(line))
                    else:
                        limited=True
            if len(buffer)>MAX_NM_LINE:
                _stop_owned(proc)
                raise ValueError("Tool produced an oversized line")
        if buffer:
            line=buffer.decode("utf-8","replace")
            if regex.search(line):
                if len(hits)<max_hits:
                    hits.append(collect_app.redact(line))
                else:
                    limited=True
        code=proc.wait(timeout=2)
        return code,hits,limited,total,collect_app.redact(tail.decode("utf-8","replace"))
    finally:
        selector.close()
        if proc.poll() is None:
            _stop_owned(proc)

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def focused_module(app,spec,filters,lookup_filters):
    path=(app/spec["relativePath"]).resolve(strict=True)
    if not path.is_relative_to(app) or path.is_symlink():
        raise ValueError("Unsafe focused module path")
    actual=sha256(path)
    if actual!=spec["sha256"]:
        return {"relativePath":spec["relativePath"],"status":"BLOCKED",
                "reason":"Module SHA-256 differs from source report; old symbol identities cannot be reused",
                "expectedSha256":spec["sha256"],"actualSha256":actual}
    regex=re.compile("|".join(re.escape(x) for x in filters),re.I)
    nm_code,hits,limited,input_bytes,nm_tail=stream_filtered(
        ["xcrun","nm","-nm",str(path)],regex)
    if nm_code:
        return {"relativePath":spec["relativePath"],"status":"FAIL",
                "reason":"nm failed","nmExitCode":nm_code,
                "nmInputBytes":input_bytes,"nmDiagnosticTail":nm_tail}
    lookup_filters=lookup_filters or filters[:12]
    pattern="("+("|".join(re.escape(x) for x in lookup_filters))+")"
    commands=["target create "+json.dumps(str(path)),"image list -t -u -f",
              "image lookup -r -n "+json.dumps(pattern)]
    # Lookup only. Raw Mach-O nlist spelling is not assumed to be LLDB's
    # callable function name or a stable ABI.
    for symbol in spec.get("symbols",[])[:16]:
        commands.append("image lookup -n "+json.dumps(symbol))
    args=["xcrun","lldb","--batch","--no-lldbinit"]
    for command in commands:
        args += ["-o",command]
    lldb_code,lldb_text=run_text(args,timeout=90)
    return {"relativePath":spec["relativePath"],
            "status":"PASS" if lldb_code==0 else "FAIL",
            "sha256":actual,"expectedUUID":spec.get("uuid"),
            "nmHits":hits,"nmLimited":limited,"nmInputBytes":input_bytes,
            "lldbExitCode":lldb_code,"lldbOutput":lldb_text,
            "limitations":["Static symbol lookup only; no AE process was launched or attached.",
                           "nm output is streamed; only matching lines are retained.",
                           "Raw nlist spelling is not treated as a callable ABI.",
                           "A resolved symbol is not yet a notification source or post-commit callback."]}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--app",type=Path,required=True)
    parser.add_argument("--targets",type=Path,default=ROOT/"focus_targets.json")
    parser.add_argument("--output",type=Path,default=Path.home()/"Desktop/FSTR-AE-Research")
    args=parser.parse_args()
    targets=json.loads(args.targets.read_text())
    app,_,meta=collect_app.identity(args.app.expanduser())
    report={"schemaVersion":1,"kind":"focused-static","application":meta,
            "sourceReportSha256":targets.get("sourceReportSha256"),
            "SYNC-001":"NOT RUN","notificationCandidate":"STATIC LEADS ONLY","modules":[]}
    filters=targets["filters"]
    lookup_filters=targets.get("lookupFilters",[])
    for spec in targets["modules"]:
        report["modules"].append(focused_module(app,spec,filters,lookup_filters))
    report["status"]="PASS" if all(x["status"]=="PASS" for x in report["modules"]) else "BLOCKED"
    out=args.output.expanduser().resolve()
    out.mkdir(parents=True,exist_ok=True)
    run_id=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid.uuid4().hex[:12]
    archive=out/("FSTR-AE-Focused-"+run_id+".zip")
    with zipfile.ZipFile(archive,"x",compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("report.json",json.dumps(collect_app.redact(report),indent=2)+"\n")
    print(report["status"]+": "+str(archive))
    return 0 if report["status"]=="PASS" else 2
if __name__=="__main__":
    raise SystemExit(main())
