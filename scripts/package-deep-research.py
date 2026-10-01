#!/usr/bin/env python3
"""Package clean read-only Deep Static research kit."""
import hashlib,json,shutil,subprocess,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; SRC=ROOT/"research/ae-notifications"
NAMES=("Deep-AE.command","deep_static.py","deep_targets.json","focused_static.py","collect_app.py")
def git(*a): return subprocess.check_output(["git","-C",str(ROOT),*a],text=True).strip()
def main():
    if git("status","--porcelain"): raise SystemExit("Dirty source: deep handoff refused")
    commit=git("rev-parse","HEAD"); out=ROOT/"dist/deep-research"/commit
    out.mkdir(parents=True,exist_ok=False); kit=out/"FSTR-AE-Deep"; kit.mkdir()
    manifest={"schemaVersion":1,"sourceCommit":commit,"sourceState":"clean",
              "buildId":"fstr-deep-"+commit[:12],"files":{}}
    for name in NAMES:
        src=SRC/name; shutil.copyfile(src,kit/name)
        (kit/name).chmod(0o755 if name.endswith(".command") else 0o644)
        manifest["files"][name]=hashlib.sha256(src.read_bytes()).hexdigest()
    (kit/"build-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    archive=out/"FSTR-AE-Deep.zip"
    with zipfile.ZipFile(archive,"x",compression=zipfile.ZIP_STORED) as z:
        for name in (*NAMES,"build-manifest.json"):
            entry=zipfile.ZipInfo("FSTR-AE-Deep/"+name,(1980,1,1,0,0,0)); entry.create_system=3
            entry.external_attr=(0o100755 if name.endswith(".command") else 0o100644)<<16
            z.writestr(entry,(kit/name).read_bytes())
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    (out/"SHA256.txt").write_text(digest+"  "+archive.name+"\n")
    if git("status","--porcelain"): raise SystemExit("Build changed source")
    print(json.dumps({"archive":str(archive),"sha256":digest,"sourceCommit":commit}))
if __name__=="__main__": main()
