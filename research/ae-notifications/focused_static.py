#!/usr/bin/env python3
"""Focused read-only static corroboration for candidates from an already collected AE report."""
from __future__ import annotations
import argparse, hashlib, json, os, plistlib, re, subprocess, sys, tempfile, uuid, zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import collect_app

MAX_TEXT = 4 * 1024 * 1024

def run_text(args, timeout=45):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    text = (result.stdout or "") + (result.stderr or "")
    if len(text.encode("utf-8", "replace")) > MAX_TEXT:
        raise ValueError("Tool output exceeded bounded limit")
    return result.returncode, collect_app.redact(text)

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk=f.read(1024*1024)
            if not chunk: break
            h.update(chunk)
    return h.hexdigest()

def focused_module(app, spec, filters):
    path=(app/spec["relativePath"]).resolve(strict=True)
    if not path.is_relative_to(app) or path.is_symlink():
        raise ValueError("Unsafe focused module path")
    actual=sha256(path)
    if actual != spec["sha256"]:
        return {"relativePath":spec["relativePath"],"status":"BLOCKED",
                "reason":"Module SHA-256 differs from the source report; do not reuse old offsets",
                "expectedSha256":spec["sha256"],"actualSha256":actual}
    regex=re.compile("|".join(re.escape(x) for x in filters),re.I)
    nm_code,nm_text=run_text(["xcrun","nm","-nm",str(path)])
    if nm_code:
        return {"relativePath":spec["relativePath"],"status":"FAIL","reason":"nm failed"}
    nm_hits=[line for line in nm_text.splitlines() if regex.search(line)]
    if len(nm_hits)>2000:
        nm_hits=nm_hits[:2000]
        nm_limited=True
    else: nm_limited=False
    commands=["target create "+json.dumps(str(path))]
    commands.append("image list -t -u -f")
    commands.append("image lookup -r -n "+json.dumps("("+("|".join(re.escape(x) for x in filters[:12]))+")"))
    for symbol in spec.get("symbols",[])[:16]:
        commands.append("image lookup -n "+json.dumps(symbol))
        commands.append("disassemble -n "+json.dumps(symbol))
    args=["xcrun","lldb","--batch","--no-lldbinit"]
    for command in commands: args += ["-o",command]
    lldb_code,lldb_text=run_text(args,timeout=90)
    return {"relativePath":spec["relativePath"],"status":"PASS" if lldb_code==0 else "FAIL",
            "sha256":actual,"expectedUUID":spec.get("uuid"),"nmHits":nm_hits,
            "nmLimited":nm_limited,"lldbExitCode":lldb_code,"lldbOutput":lldb_text,
            "limitations":["Static symbol/disassembly evidence only; no AE process was launched or attached.",
                           "A referenced function is not yet a notification source or post-commit callback."]}

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
    for spec in targets["modules"]:
        report["modules"].append(focused_module(app,spec,targets["filters"]))
    report["status"]="PASS" if all(x["status"]=="PASS" for x in report["modules"]) else "BLOCKED"
    out=args.output.expanduser().resolve(); out.mkdir(parents=True,exist_ok=True)
    run_id=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid.uuid4().hex[:12]
    archive=out/("FSTR-AE-Focused-"+run_id+".zip")
    with zipfile.ZipFile(archive,"x",compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("report.json",json.dumps(collect_app.redact(report),indent=2)+"\n")
    print(report["status"]+": "+str(archive))
    return 0 if report["status"]=="PASS" else 2

if __name__=="__main__":
    raise SystemExit(main())
