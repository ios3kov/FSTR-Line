#!/usr/bin/env python3
"""Exact-build, read-only deep static research for AE internal candidates."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess, sys, uuid, zipfile
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import collect_app
import focused_static

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def run_text(args,timeout=90,max_bytes=32*1024*1024):
    done=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
    text=(done.stdout or "")+(done.stderr or "")
    if len(text.encode("utf-8","replace"))>max_bytes:
        raise ValueError("Bounded tool output exceeded")
    return done.returncode,collect_app.redact(text)

def module_uuid(path):
    code,text=run_text(["xcrun","dwarfdump","--uuid",str(path)],timeout=30,max_bytes=1024*1024)
    if code:
        raise RuntimeError("dwarfdump failed")
    match=re.search(r"UUID:\s*([0-9A-Fa-f-]{36})",text)
    if not match:
        raise RuntimeError("Mach-O UUID unavailable")
    return str(uuid.UUID(match.group(1))).lower()

def verify_module(app,key,spec):
    path=(app/spec["relativePath"]).resolve(strict=True)
    if not path.is_relative_to(app) or path.is_symlink():
        raise ValueError("Unsafe module path: "+key)
    actual_sha=sha256(path)
    actual_uuid=module_uuid(path)
    expected_uuid=str(uuid.UUID(spec["uuid"])).lower()
    if actual_sha!=spec["sha256"] or actual_uuid!=expected_uuid:
        return None,{"status":"BLOCKED","module":key,"relativePath":spec["relativePath"],
            "expectedSha256":spec["sha256"],"actualSha256":actual_sha,
            "expectedUUID":expected_uuid,"actualUUID":actual_uuid}
    return path,{"status":"PASS","module":key,"relativePath":spec["relativePath"],
        "sha256":actual_sha,"uuid":actual_uuid}

def active_candidates(path,regex_text,limits):
    regex=re.compile(regex_text)
    code,hits,limited,input_bytes,tail=focused_static.stream_filtered(
        ["xcrun","nm","-nm","-C",str(path)],regex,timeout=120,
        max_input=int(limits["maxNmInputBytes"]),max_hits=int(limits["maxNmHits"]))
    return {"exitCode":code,"hits":hits,"limited":limited,"inputBytes":input_bytes,
            "diagnosticTail":tail if code else ""}

def lldb_known(path,functions,max_bytes):
    commands=["target create "+json.dumps(str(path)),"image list -t -u -f"]
    for item in functions:
        if item.get("name"):
            commands.append("image lookup -n "+json.dumps(item["name"]))
            commands.append("disassemble -n "+json.dumps(item["name"]))
        elif item.get("nameRegex"):
            commands.append("image lookup -r -n "+json.dumps(item["nameRegex"]))
    args=["xcrun","lldb","--batch","--no-lldbinit"]
    for c in commands:
        args.extend(["-o",c])
    code,text=run_text(args,timeout=120,max_bytes=max_bytes)
    return {"exitCode":code,"output":text}

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--app",type=Path,required=True)
    p.add_argument("--targets",type=Path,default=ROOT/"deep_targets.json")
    p.add_argument("--output",type=Path,default=Path.home()/"Desktop/FSTR-AE-Research")
    args=p.parse_args(argv)
    targets=json.loads(args.targets.read_text(encoding="utf-8"))
    app,_,meta=collect_app.identity(args.app.expanduser())
    if (meta.get("bundleId")!=targets["aeBundleId"] or
        meta.get("shortVersion")!=targets["aeShortVersion"] or
        meta.get("bundleVersion")!=targets["aeBundleVersion"]):
        raise SystemExit("BLOCKED: deep research is pinned to exact AE 25.6.0.101")
    report={"schemaVersion":1,"kind":"deep-static","status":"PASS",
            "application":meta,"modules":[],"activeCompCandidates":{},
            "knownFunctionStatic":{},"SYNC-001":"NOT RUN",
            "claims":{"notificationSource":"UNPROVEN","postCommit":"UNPROVEN","activeComp":"UNPROVEN"},
            "limitations":[
                "Static symbol names and disassembly are leads, not notification coverage.",
                "No AE process is launched or attached.",
                "No binary, project, preference or security setting is modified.",
                "A private call target is not a supported ABI or production subscription mechanism."
            ]}
    verified={}
    for key,spec in targets["modules"].items():
        path,row=verify_module(app,key,spec)
        report["modules"].append(row)
        if path is None:
            report["status"]="BLOCKED"
        else:
            verified[key]=path
    if report["status"]=="PASS":
        limits=targets["limits"]
        for key,path in verified.items():
            report["activeCompCandidates"][key]=active_candidates(path,targets["activeCompRegex"],limits)
            funcs=[x for x in targets["knownFunctions"] if x["module"]==key]
            if funcs:
                report["knownFunctionStatic"][key]=lldb_known(
                    path,funcs,int(limits["maxLldbOutputBytes"]))
    out=args.output.expanduser().resolve(); out.mkdir(parents=True,exist_ok=True)
    run_id=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid.uuid4().hex[:12]
    archive=out/("FSTR-AE-Deep-"+run_id+".zip")
    with zipfile.ZipFile(archive,"x",compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("report.json",json.dumps(collect_app.redact(report),indent=2)+"\n")
    print(report["status"]+": "+str(archive))
    return 0 if report["status"]=="PASS" else 2

if __name__=="__main__":
    raise SystemExit(main())
