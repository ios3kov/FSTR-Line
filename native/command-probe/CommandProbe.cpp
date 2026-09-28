#include "CommandProbe.h"

#include <cstdio>
#include <cstdlib>
#include <ctime>
#include <chrono>
#include <type_traits>
#include "ProbeBuild.h"

static AEGP_PluginID g_plugin_id = 0;
static FILE *g_log = nullptr;
static unsigned long g_sequence = 0;
static std::chrono::steady_clock::time_point g_start;

static const char *log_path()
{
    const char *path = std::getenv("FSTR_COMMAND_PROBE_LOG");
    return path && path[0] ? path : nullptr;
}

static void log_event(const char *kind, AEGP_Command command, AEGP_HookPriority priority,
                      A_Boolean already_handled)
{
    if (!g_log) return;
    const auto elapsed = std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::steady_clock::now() - g_start).count();
    if (elapsed > 600000000 || g_sequence >= 100000) {
        std::fprintf(g_log, "{\"kind\":\"captureLimit\"}\n");
        std::fclose(g_log);
        g_log = nullptr;
        return;
    }
    std::fprintf(g_log,
                 "{\"buildId\":\"%s\",\"sequence\":%lu,\"elapsedUs\":%lld,\"unixTime\":%lld,\"kind\":\"%s\",\"command\":%ld,\"requestedPriority\":1,\"priority\":%lu,\"alreadyHandled\":%d}\n",
                 FSTR_PROBE_BUILD_ID, ++g_sequence, static_cast<long long>(elapsed),
                 static_cast<long long>(std::time(nullptr)), kind,
                 static_cast<long>(command), static_cast<unsigned long>(priority),
                 already_handled ? 1 : 0);
    std::fflush(g_log);
}

static A_Err command_hook(AEGP_GlobalRefcon, AEGP_CommandRefcon,
                          AEGP_Command command, AEGP_HookPriority priority,
                          A_Boolean already_handled, A_Boolean *handled)
{
    if (handled) *handled = FALSE;
    log_event("command", command, priority, already_handled);
    return A_Err_NONE;
}

static A_Err death_hook(AEGP_GlobalRefcon, AEGP_DeathRefcon)
{
    log_event("death", -1, 0, FALSE);
    if (g_log) std::fclose(g_log);
    g_log = nullptr;
    return A_Err_NONE;
}

extern "C" DllExport A_Err EntryPointFunc(
    SPBasicSuite *basic, A_long, A_long,
    AEGP_PluginID plugin_id, AEGP_GlobalRefcon *refcon)
{
    if (refcon) *refcon = nullptr;
    // AE assigns this opaque ID and requires the exact value for every suite
    // registration. Do not leave it at the static zero initializer.
    g_plugin_id = plugin_id;
    g_start = std::chrono::steady_clock::now();
    // Explicit, unique capture path required; never append to a previous run.
    if (!log_path()) return A_Err_GENERIC;
    g_log = std::fopen(log_path(), "wx");
    if (!g_log) return A_Err_GENERIC;
    AEGP_SuiteHandler suites(basic);
    A_Err err = A_Err_NONE;
    ERR(suites.RegisterSuite5()->AEGP_RegisterCommandHook(
        g_plugin_id, AEGP_HP_BeforeAE, AEGP_Command_ALL, command_hook, nullptr));
    ERR(suites.RegisterSuite5()->AEGP_RegisterDeathHook(g_plugin_id, death_hook, nullptr));
    log_event(err ? "registrationFailed" : "loaded", err, 0, FALSE);
    return err;
}
static_assert(std::is_same<decltype(&EntryPointFunc), AEGP_PluginInitFunc>::value,
              "Entry point must match the current AE SDK ABI");
