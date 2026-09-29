#include "PluginOrigin.h"

#include <chrono>
#include <cstdio>
#include <cstring>
#include <ctime>
#include <type_traits>
#include <unistd.h>
#include "PluginOriginBuild.h"

static SPBasicSuite *g_basic = nullptr;
static AEGP_PluginID g_plugin_id = 0;
static AEGP_Command g_command = 0;
static FILE *g_log = nullptr;
static unsigned long g_sequence = 0;
static std::chrono::steady_clock::time_point g_started;

static long long wall_time_ns()
{
    return std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
}

static long long elapsed_us()
{
    return std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::steady_clock::now() - g_started).count();
}

static void log_status(const char *kind, long status_code)
{
    if (!g_log) return;
    std::fprintf(g_log,
        "{\"buildId\":\"%s\",\"sequence\":%lu,\"kind\":\"%s\","
        "\"wallTimeNs\":%lld,\"elapsedUs\":%lld,\"statusCode\":%ld}\n",
        FSTR_PLUGIN_ORIGIN_BUILD_ID, ++g_sequence, kind,
        wall_time_ns(), elapsed_us(), status_code);
    std::fflush(g_log);
}

static void log_mutation(const char *kind, A_long layer_index,
                         A_Boolean before_video, A_Boolean after_video,
                         A_Err status_code)
{
    if (!g_log) return;
    std::fprintf(g_log,
        "{\"buildId\":\"%s\",\"sequence\":%lu,\"kind\":\"%s\","
        "\"wallTimeNs\":%lld,\"elapsedUs\":%lld,\"layerIndex\":%ld,"
        "\"beforeVideoActive\":%d,\"afterVideoActive\":%d,\"statusCode\":%ld}\n",
        FSTR_PLUGIN_ORIGIN_BUILD_ID, ++g_sequence, kind,
        wall_time_ns(), elapsed_us(), static_cast<long>(layer_index),
        before_video ? 1 : 0, after_video ? 1 : 0, static_cast<long>(status_code));
    std::fflush(g_log);
}

static bool current_target(AEGP_SuiteHandler &suites,
                           AEGP_LayerH *layerPH, A_long *indexPL)
{
    if (!layerPH || !indexPL) return false;
    *layerPH = nullptr;
    *indexPL = -1;

    AEGP_ItemH itemH = nullptr;
    AEGP_ItemType type = AEGP_ItemType_NONE;
    AEGP_CompH compH = nullptr;
    A_long count = 0;

    if (suites.ItemSuite9()->AEGP_GetActiveItem(&itemH) != A_Err_NONE || !itemH) return false;
    if (suites.ItemSuite9()->AEGP_GetItemType(itemH, &type) != A_Err_NONE ||
        type != AEGP_ItemType_COMP) return false;
    if (suites.CompSuite12()->AEGP_GetCompFromItem(itemH, &compH) != A_Err_NONE || !compH) return false;
    if (suites.LayerSuite9()->AEGP_GetCompNumLayers(compH, &count) != A_Err_NONE || count < 1) return false;
    if (suites.LayerSuite9()->AEGP_GetCompLayerByIndex(compH, 0, layerPH) != A_Err_NONE || !*layerPH) return false;
    *indexPL = 0;
    return true;
}

static A_Err update_menu_hook(AEGP_GlobalRefcon, AEGP_UpdateMenuRefcon, AEGP_WindowType)
{
    if (!g_basic || !g_command) return A_Err_NONE;
    AEGP_SuiteHandler suites(g_basic);
    AEGP_LayerH layerH = nullptr;
    A_long index = -1;
    if (current_target(suites, &layerH, &index)) {
        return suites.CommandSuite1()->AEGP_EnableCommand(g_command);
    }
    return suites.CommandSuite1()->AEGP_DisableCommand(g_command);
}

static A_Err mutate_first_layer()
{
    AEGP_SuiteHandler suites(g_basic);
    AEGP_LayerH layerH = nullptr;
    A_long index = -1;
    if (!current_target(suites, &layerH, &index)) {
        log_status("noTarget", A_Err_GENERIC);
        return A_Err_NONE;
    }

    AEGP_LayerFlags flags = AEGP_LayerFlag_NONE;
    A_Err err = suites.LayerSuite9()->AEGP_GetLayerFlags(layerH, &flags);
    if (err != A_Err_NONE) {
        log_status("getFlagsFailed", err);
        return err;
    }
    const A_Boolean before = (flags & AEGP_LayerFlag_VIDEO_ACTIVE) ? TRUE : FALSE;
    const A_Boolean desired = before ? FALSE : TRUE;
    log_mutation("mutationStart", index, before, before, A_Err_NONE);

    bool undo_started = false;
    err = suites.UtilitySuite6()->AEGP_StartUndoGroup("FSTR Plugin Origin Test");
    if (err == A_Err_NONE) {
        undo_started = true;
        err = suites.LayerSuite9()->AEGP_SetLayerFlag(
            layerH, AEGP_LayerFlag_VIDEO_ACTIVE, desired);
    }

    A_Err end_err = A_Err_NONE;
    if (undo_started) {
        end_err = suites.UtilitySuite6()->AEGP_EndUndoGroup();
        if (err == A_Err_NONE && end_err != A_Err_NONE) err = end_err;
    }

    AEGP_LayerFlags after_flags = flags;
    const A_Err get_after_err =
        suites.LayerSuite9()->AEGP_GetLayerFlags(layerH, &after_flags);
    if (err == A_Err_NONE && get_after_err != A_Err_NONE) err = get_after_err;
    const A_Boolean after =
        (after_flags & AEGP_LayerFlag_VIDEO_ACTIVE) ? TRUE : FALSE;
    log_mutation("mutationEnd", index, before, after, err);
    return err;
}

static A_Err command_hook(AEGP_GlobalRefcon, AEGP_CommandRefcon,
                          AEGP_Command command, AEGP_HookPriority,
                          A_Boolean, A_Boolean *handledPB)
{
    if (handledPB) *handledPB = FALSE;
    if (command != g_command) return A_Err_NONE;
    if (handledPB) *handledPB = TRUE;
    return mutate_first_layer();
}

static A_Err death_hook(AEGP_GlobalRefcon, AEGP_DeathRefcon)
{
    log_status("death", A_Err_NONE);
    if (g_log) {
        std::fclose(g_log);
        g_log = nullptr;
    }
    return A_Err_NONE;
}

extern "C" DllExport A_Err EntryPointFunc(
    SPBasicSuite *basic, A_long, A_long,
    AEGP_PluginID plugin_id, AEGP_GlobalRefcon *refcon)
{
    if (refcon) *refcon = nullptr;
    g_basic = basic;
    g_plugin_id = plugin_id;
    g_started = std::chrono::steady_clock::now();

    char path[1024] = {0};
    std::snprintf(path, sizeof(path), "/tmp/FSTRPluginOrigin-%ld-%s.jsonl",
                  static_cast<long>(getpid()), FSTR_PLUGIN_ORIGIN_BUILD_ID);
    g_log = std::fopen(path, "wx");
    if (!g_log) return A_Err_GENERIC;

    AEGP_SuiteHandler suites(basic);
    A_Err err = suites.CommandSuite1()->AEGP_GetUniqueCommand(&g_command);
    if (err == A_Err_NONE) {
        err = suites.CommandSuite1()->AEGP_InsertMenuCommand(
            g_command, "FSTR Plugin Origin Test",
            AEGP_Menu_WINDOW, AEGP_MENU_INSERT_SORTED);
    }
    if (err == A_Err_NONE) {
        err = suites.RegisterSuite5()->AEGP_RegisterCommandHook(
            g_plugin_id, AEGP_HP_BeforeAE, AEGP_Command_ALL,
            command_hook, nullptr);
    }
    if (err == A_Err_NONE) {
        err = suites.RegisterSuite5()->AEGP_RegisterUpdateMenuHook(
            g_plugin_id, update_menu_hook, nullptr);
    }
    if (err == A_Err_NONE) {
        err = suites.RegisterSuite5()->AEGP_RegisterDeathHook(
            g_plugin_id, death_hook, nullptr);
    }

    log_status(err == A_Err_NONE ? "loaded" : "registrationFailed", err);
    if (err != A_Err_NONE && g_log) {
        std::fclose(g_log);
        g_log = nullptr;
    }
    return err;
}

static_assert(std::is_same<decltype(&EntryPointFunc), AEGP_PluginInitFunc>::value,
              "Entry point must match the current AE SDK ABI");
