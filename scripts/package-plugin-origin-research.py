#!/usr/bin/env python3
"""Package clean Plugin Origin diagnostic build/install/observe kit."""
import hashlib,json,shutil,subprocess,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; SRC=ROOT/'research/ae-notifications'; NATIVE=ROOT/'native/plugin-origin'
FILES={
 'Build-Install.command':SRC/'Build-PluginOrigin.command',
 'Observe.command':SRC/'Observe-PluginOrigin.command',
 'Uninstall.command':SRC/'Uninstall-PluginOrigin.command',
 'plugin_origin_tool.py':SRC/'plugin_origin_tool.py',
 'plugin_origin_targets.json':SRC/'plugin_origin_targets.json',
 'PluginOrigin.cpp':NATIVE/'PluginOrigin.cpp',
 'PluginOrigin.h':NATIVE/'PluginOrigin.h',
 'PluginOrigin_PiPL.r':NATIVE/'PluginOrigin_PiPL.r',
 'runtime_control.py':SRC/'runtime_control.py',
 'trace_callback.py':SRC/'trace_callback.py',
 'runtime_protocol.py':SRC/'runtime_protocol.py',
 'collect_app.py':SRC/'collect_app.py',
 'FSTR-Snapshot.jsx':SRC/'FSTR-Snapshot.jsx',
}
def git(*a): return subprocess.check_output(['git','-C',str(ROOT),*a],text=True).strip()
def main():
    if git('status','--porcelain'): raise SystemExit('Dirty source: Plugin Origin handoff refused')
    commit=git('rev-parse','HEAD'); out=ROOT/'dist/plugin-origin-research'/commit
    out.mkdir(parents=True,exist_ok=False); kit=out/'FSTR-AE-PluginOrigin'; kit.mkdir()
    manifest={'schemaVersion':1,'sourceCommit':commit,'sourceState':'clean','buildId':'fstr-plugin-origin-kit-'+commit[:12],'files':{}}
    for name,src in FILES.items():
        shutil.copyfile(src,kit/name); (kit/name).chmod(0o755 if name.endswith('.command') else 0o644)
        manifest['files'][name]=hashlib.sha256(src.read_bytes()).hexdigest()
    (kit/'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    archive=out/'FSTR-AE-PluginOrigin.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_STORED) as z:
        for name in (*FILES.keys(),'build-manifest.json'):
            entry=zipfile.ZipInfo('FSTR-AE-PluginOrigin/'+name,(1980,1,1,0,0,0)); entry.create_system=3
            entry.external_attr=(0o100755 if name.endswith('.command') else 0o100644)<<16
            z.writestr(entry,(kit/name).read_bytes())
    digest=hashlib.sha256(archive.read_bytes()).hexdigest(); (out/'SHA256.txt').write_text(digest+'  '+archive.name+'\n')
    if git('status','--porcelain'): raise SystemExit('Build changed source')
    print(json.dumps({'archive':str(archive),'sha256':digest,'sourceCommit':commit}))
if __name__=='__main__': main()
