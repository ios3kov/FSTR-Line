"""Mac compile/package smoke for PluginOrigin source using ABI-shaped fake suites. Never Adobe."""
import json,subprocess,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    if sys.platform!='darwin': raise SystemExit('BLOCKED')
    commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    archive=ROOT/'dist/plugin-origin-research'/commit/'FSTR-AE-PluginOrigin.zip'
    with tempfile.TemporaryDirectory(prefix='fstr-plugin-origin-smoke-') as td:
        t=Path(td)
        with zipfile.ZipFile(archive) as z:z.extractall(t/'kit')
        kit=t/'kit/FSTR-AE-PluginOrigin'; inc=t/'fake'; inc.mkdir()
        (inc/'AEConfig.h').write_text('')
        (inc/'entry.h').write_text('#define DllExport __attribute__((visibility("default")))\n')
        (inc/'AE_Macros.h').write_text('')
        (inc/'AE_GeneralPlug.h').write_text(r'''
#pragma once
using A_Err=int; using A_long=long; using A_Boolean=int; using AEGP_PluginID=long;
using AEGP_Command=long; using AEGP_HookPriority=long; using AEGP_WindowType=long;
using AEGP_GlobalRefcon=void*; using AEGP_CommandRefcon=void*; using AEGP_UpdateMenuRefcon=void*; using AEGP_DeathRefcon=void*;
using AEGP_ItemH=void*; using AEGP_CompH=void*; using AEGP_LayerH=void*; using AEGP_LayerFlags=long; using AEGP_ItemType=long;
struct SPBasicSuite {};
constexpr A_Err A_Err_NONE=0, A_Err_GENERIC=1; constexpr A_Boolean TRUE=1,FALSE=0;
constexpr AEGP_ItemType AEGP_ItemType_NONE=-1, AEGP_ItemType_COMP=4;
constexpr AEGP_LayerFlags AEGP_LayerFlag_NONE=0, AEGP_LayerFlag_VIDEO_ACTIVE=1;
constexpr long AEGP_Menu_WINDOW=1, AEGP_MENU_INSERT_SORTED=1, AEGP_HP_BeforeAE=1, AEGP_Command_ALL=0;
using AEGP_CommandHook=A_Err(*)(AEGP_GlobalRefcon,AEGP_CommandRefcon,AEGP_Command,AEGP_HookPriority,A_Boolean,A_Boolean*);
using AEGP_UpdateMenuHook=A_Err(*)(AEGP_GlobalRefcon,AEGP_UpdateMenuRefcon,AEGP_WindowType);
using AEGP_DeathHook=A_Err(*)(AEGP_GlobalRefcon,AEGP_DeathRefcon);
using AEGP_PluginInitFunc=A_Err(*)(SPBasicSuite*,A_long,A_long,AEGP_PluginID,AEGP_GlobalRefcon*);
''')
        (inc/'AEGP_SuiteHandler.h').write_text(r'''
#pragma once
#include "AE_GeneralPlug.h"
struct Cmd { A_Err AEGP_GetUniqueCommand(AEGP_Command*); A_Err AEGP_InsertMenuCommand(AEGP_Command,const char*,long,long); A_Err AEGP_EnableCommand(AEGP_Command); A_Err AEGP_DisableCommand(AEGP_Command); };
struct Reg { A_Err AEGP_RegisterCommandHook(AEGP_PluginID,AEGP_HookPriority,AEGP_Command,AEGP_CommandHook,void*); A_Err AEGP_RegisterUpdateMenuHook(AEGP_PluginID,AEGP_UpdateMenuHook,void*); A_Err AEGP_RegisterDeathHook(AEGP_PluginID,AEGP_DeathHook,void*); };
struct Item { A_Err AEGP_GetActiveItem(AEGP_ItemH*); A_Err AEGP_GetItemType(AEGP_ItemH,AEGP_ItemType*); };
struct Comp { A_Err AEGP_GetCompFromItem(AEGP_ItemH,AEGP_CompH*); };
struct Layer { A_Err AEGP_GetCompNumLayers(AEGP_CompH,A_long*); A_Err AEGP_GetCompLayerByIndex(AEGP_CompH,A_long,AEGP_LayerH*); A_Err AEGP_GetLayerFlags(AEGP_LayerH,AEGP_LayerFlags*); A_Err AEGP_SetLayerFlag(AEGP_LayerH,AEGP_LayerFlags,A_Boolean); };
struct Util { A_Err AEGP_StartUndoGroup(const char*); A_Err AEGP_EndUndoGroup(); };
struct AEGP_SuiteHandler { AEGP_SuiteHandler(SPBasicSuite*); Cmd* CommandSuite1(); Reg* RegisterSuite5(); Item* ItemSuite9(); Comp* CompSuite12(); Layer* LayerSuite9(); Util* UtilitySuite6(); };
''')
        (inc/'PluginOriginBuild.h').write_text('#define FSTR_PLUGIN_ORIGIN_BUILD_ID "fixture"\n')
        src=kit/'PluginOrigin.cpp'; hdr=kit/'PluginOrigin.h'
        local=t/'src'; local.mkdir()
        for f in (src,hdr): (local/f.name).write_bytes(f.read_bytes())
        (local/'PluginOriginBuild.h').write_bytes((inc/'PluginOriginBuild.h').read_bytes())
        subprocess.run(['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-I',str(inc),'-I',str(local),'-c',str(local/'PluginOrigin.cpp'),'-o',str(t/'origin.o')],check=True,timeout=60)
        for script in ('Build-Install.command','Observe.command','Uninstall.command'):
            subprocess.run(['/bin/bash','-n',str(kit/script)],check=True,timeout=10)
        ev={'status':'PASS','scope':'PluginOrigin C++ compile against ABI-shaped fake suites + package scripts, NOT Adobe SDK/AE','sourceCommit':commit,'SYNC-001':'NOT RUN'}
        dest=ROOT/'dist/notification-evidence/plugin-origin-smoke.json'; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_text(json.dumps(ev,indent=2)+'\n'); print(json.dumps(ev))
if __name__=='__main__':main()
