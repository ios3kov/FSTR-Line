#!/usr/bin/env python3
"""Package the focused static research kit from a clean commit."""
import hashlib, json, shutil, subprocess, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"research/ae-notifications"
NAMES=("Focus-AE.command","focused_static.py","focus_targets.json","collect_app.py")
def git(*args): return subprocess.check_output(["git","-C",str(ROOT),*args],text=True).strip()
def main():
    if git("status","--porcelain"): raise SystemExit("Dirty source: focused handoff refused")
    commit=git("rev-parse","HEAD")
    out=ROOT/"dist/focused-research"/commit
    out.mkdir(parents=True,exist_ok=False)
    kit=out/"FSTR-AE-Focused"; kit.mkdir()
    manifest={"schemaVersion":1,"sourceCommit":commit,"sourceState":"clean",
              "buildId":"fstr-focused-"+commit[:12],"files":{}}
    for name in NAMES:
        src=SRC/name
        shutil.copyfile(src,kit/name)
        (kit/name).chmod(0o755 if name.endswith(".command") else 0o644)
        manifest["files"][name]=hashlib.sha256(src.read_bytes()).hexdigest()
    (kit/"build-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    archive=out/"FSTR-AE-Focused.zip"
    with zipfile.ZipFile(archive,"x",compression=zipfile.ZIP_STORED) as z:
        for name in (*NAMES,"build-manifest.json"):
            entry=zipfile.ZipInfo("FSTR-AE-Focused/"+name,(1980,1,1,0,0,0))
            entry.create_system=3
            entry.external_attr=(0o100755 if name.endswith(".command") else 0o100644)<<16
            z.writestr(entry,(kit/name).read_bytes())
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    (out/"SHA256.txt").write_text(digest+"  "+archive.name+"\n")
    if git("status","--porcelain"): raise SystemExit("Build changed source")
    print(json.dumps({"archive":str(archive),"sha256":digest,"sourceCommit":commit}))
if __name__=="__main__": main()
