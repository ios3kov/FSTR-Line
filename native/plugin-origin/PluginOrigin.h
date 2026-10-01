#pragma once
#include "AEConfig.h"
#include "entry.h"
#include "AE_GeneralPlug.h"
#include "AE_Macros.h"
#include "AEGP_SuiteHandler.h"

extern "C" DllExport A_Err EntryPointFunc(
    SPBasicSuite *, A_long, A_long, AEGP_PluginID, AEGP_GlobalRefcon *);
