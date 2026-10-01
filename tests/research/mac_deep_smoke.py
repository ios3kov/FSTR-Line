"""Mac-only smoke for Deep Static on owned Mach-O fixtures. Never Adobe."""
import hashlib,json,plistlib,subprocess,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def uuid_of(path):
    text=subprocess.check_output(["xcrun","dwarfdump","--uuid",str(path)],text=True)
    return text.split("UUID: ",1)[1].split(" ",1)[0].lower()
def main():
    if sys.platform!="darwin": raise SystemExit("BLOCKED")
    commit=subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True).strip()
    archive=ROOT/"dist/deep-research"/commit/"FSTR-AE-Deep.zip"
    with tempfile.TemporaryDirectory(prefix="fstr-deep-") as td:
        t=Path(td)
        with zipfile.ZipFile(archive) as z: z.extractall(t/"kit")
        kit=t/"kit/FSTR-AE-Deep"; app=t/"Fixture.app"
        bee=app/"Contents/Frameworks/BEE.dylib"; aft=app/"Contents/Frameworks/AfterFXLib.framework/Versions/A/AfterFXLib"
        bee.parent.mkdir(parents=True); aft.parent.mkdir(parents=True)
        src1=t/"bee.cpp"; src1.write_text(
            '__attribute__((noinline)) void DoProcessProjectChanges(unsigned long long x){asm volatile(""::"r"(x));}\n'
            'struct BEE_ThreadedRenderUpdateQueue{__attribute__((noinline)) void Render_EndUndoGroup();};\n'
            'void BEE_ThreadedRenderUpdateQueue::Render_EndUndoGroup(){}\n'
            'extern "C" __attribute__((noinline)) void BEE_CmdSeekItemToTime(){}\n'
            'int main(){DoProcessProjectChanges(1); BEE_ThreadedRenderUpdateQueue q; q.Render_EndUndoGroup(); BEE_CmdSeekItemToTime();}\n')
        src2=t/"aft.cpp"; src2.write_text(
            '__attribute__((noinline)) void SetActiveComposition(){}\n'
            'struct CCompPano{__attribute__((noinline)) void Activate();};\n'
            'void CCompPano::Activate(){}\nint main(){SetActiveComposition(); CCompPano c; c.Activate();}\n')
        subprocess.run(["xcrun","clang++","-g","-O0",str(src1),"-o",str(bee)],check=True,timeout=60)
        subprocess.run(["xcrun","clang++","-g","-O0",str(src2),"-o",str(aft)],check=True,timeout=60)
        mac=app/"Contents/MacOS"; mac.mkdir(parents=True); (mac/"After Effects").write_bytes(bee.read_bytes())
        (app/"Contents/Info.plist").write_bytes(plistlib.dumps({
          "CFBundleIdentifier":"com.adobe.AfterEffects.application","CFBundleShortVersionString":"25.6.0",
          "CFBundleVersion":"25.6.0.101","CFBundleExecutable":"After Effects"}))
        targets={
          "schemaVersion":1,"aeBundleId":"com.adobe.AfterEffects.application","aeShortVersion":"25.6.0","aeBundleVersion":"25.6.0.101",
          "modules":{
            "BEE":{"relativePath":"Contents/Frameworks/BEE.dylib","sha256":hashlib.sha256(bee.read_bytes()).hexdigest(),"uuid":uuid_of(bee)},
            "AfterFXLib":{"relativePath":"Contents/Frameworks/AfterFXLib.framework/Versions/A/AfterFXLib","sha256":hashlib.sha256(aft.read_bytes()).hexdigest(),"uuid":uuid_of(aft)}
          },
          "knownFunctions":[
            {"module":"BEE","name":"DoProcessProjectChanges(unsigned long long)","fileAddress":"0x0"},
            {"module":"BEE","nameRegex":"BEE_CmdSeekItemToTime","fileAddress":"0x0"}
          ],
          "activeCompRegex":"(?i)((active|activate|current|front).*(comp|composition|item|viewer|pano))|((comp|composition|item|viewer|pano).*(active|activate|current|front))",
          "limits":{"maxNmInputBytes":16777216,"maxNmHits":100,"maxLldbOutputBytes":8388608}
        }
        tp=t/"targets.json"; tp.write_text(json.dumps(targets)); out=t/"out"
        done=subprocess.run(["python3","-I","-B",str(kit/"deep_static.py"),"--app",str(app),
                             "--targets",str(tp),"--output",str(out)],capture_output=True,text=True,timeout=180)
        if done.returncode:
            raise RuntimeError(done.stdout+done.stderr)
        reports=list(out.glob("*.zip")); assert len(reports)==1
        with zipfile.ZipFile(reports[0]) as z: report=json.loads(z.read("report.json"))
        assert report["status"]=="PASS" and report["SYNC-001"]=="NOT RUN"
        assert any("ActiveComposition" in x or "CCompPano" in x
                   for x in report["activeCompCandidates"]["AfterFXLib"]["hits"])
        static=report["knownFunctionStatic"]["BEE"]
        assert "DoProcessProjectChanges" in static["output"]
        assert static["exitCode"]==0
        ev={"status":"PASS","scope":"Deep Static exact-hash/UUID lookup + disassembly on owned Mach-O, NOT AE",
            "sourceCommit":commit,"SYNC-001":"NOT RUN"}
        dest=ROOT/"dist/notification-evidence/deep-smoke.json"; dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps(ev,indent=2)+"\n"); print(json.dumps(ev))
if __name__=="__main__": main()
