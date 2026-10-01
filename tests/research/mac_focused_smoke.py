"""Run the exact focused kit on an owned Mach-O fixture. Not Adobe evidence."""
import hashlib,json,plistlib,subprocess,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    if sys.platform!="darwin": raise SystemExit("BLOCKED")
    commit=subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True).strip()
    archive=ROOT/"dist/focused-research"/commit/"FSTR-AE-Focused.zip"
    with tempfile.TemporaryDirectory(prefix="fstr-focus-") as td:
        t=Path(td)
        with zipfile.ZipFile(archive) as z: z.extractall(t/"kit")
        kit=t/"kit/FSTR-AE-Focused"; app=t/"Fixture.app"
        mod=app/"Contents/Frameworks/BEE.dylib"; mod.parent.mkdir(parents=True)
        src=t/"fixture.cpp"; src.write_text('extern "C" __attribute__((noinline)) void BEE_Layer_CmdParamChanged(){}\nint main(){BEE_Layer_CmdParamChanged();}\n')
        subprocess.run(["xcrun","clang++","-g","-O0",str(src),"-o",str(mod)],check=True,timeout=60)
        (app/"Contents/MacOS").mkdir(); (app/"Contents/MacOS/After Effects").write_bytes(mod.read_bytes())
        (app/"Contents/Info.plist").write_bytes(plistlib.dumps({
            "CFBundleIdentifier":"com.adobe.AfterEffects.application","CFBundleShortVersionString":"25.6.0",
            "CFBundleVersion":"SYNTHETIC-NOT-ADOBE","CFBundleExecutable":"After Effects"}))
        target={"schemaVersion":1,"sourceReportSha256":"fixture","aeBuild":"fixture",
                "modules":[{"relativePath":"Contents/Frameworks/BEE.dylib",
                            "sha256":hashlib.sha256(mod.read_bytes()).hexdigest(),"uuid":"fixture",
                            "symbols":["BEE_Layer_CmdParamChanged"]}],
                "filters":["BEE_Layer","CmdParamChanged"]}
        targets=t/"targets.json"; targets.write_text(json.dumps(target)); out=t/"out"
        done=subprocess.run(["python3","-I","-B",str(kit/"focused_static.py"),"--app",str(app),
                             "--targets",str(targets),"--output",str(out)],capture_output=True,text=True,timeout=120)
        if done.returncode:
            reports=list(out.glob("*.zip"))
            detail=""
            if reports:
                with zipfile.ZipFile(reports[0]) as z: detail=z.read("report.json").decode()
            raise RuntimeError(done.stdout+done.stderr+detail)
        reports=list(out.glob("*.zip")); assert len(reports)==1
        with zipfile.ZipFile(reports[0]) as z: report=json.loads(z.read("report.json"))
        row=report["modules"][0]
        assert report["status"]=="PASS" and report["SYNC-001"]=="NOT RUN"
        assert row["status"]=="PASS" and any("BEE_Layer" in x for x in row["nmHits"])
        assert "BEE_Layer_CmdParamChanged" in row["lldbOutput"]
        evidence={"status":"PASS","scope":"exact focused kit nm/LLDB lookup on owned Mach-O, NOT AE",
                  "sourceCommit":commit,"SYNC-001":"NOT RUN"}
        dest=ROOT/"dist/notification-evidence/focused-smoke.json"; dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps(evidence,indent=2)+"\n"); print(json.dumps(evidence))
if __name__=="__main__": main()
