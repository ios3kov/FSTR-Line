// Research AEGP shell. Default builds cannot register a private BEE callback.
// SDK headers are external inputs and are never vendored into this repository.
#if defined(__APPLE__)
#include <CoreServices/CoreServices.h>
#endif
#include "AEConfig.h"
#include "AE_GeneralPlug.h"
#include "dispatch.hpp"
#include "binding.hpp"
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <new>
#include <type_traits>
#include <unistd.h>
#ifndef FSTR_PROBE_BUILD_ID
#error "Build identity must be supplied by the checked build script"
#endif
#ifndef FSTR_ENABLE_PRIVATE_CHAIN_PROBE
#define FSTR_ENABLE_PRIVATE_CHAIN_PROBE 0
#endif

namespace fstr::research {
namespace {
struct Sample { A_Boolean has_layer=0; AEGP_LayerIDVal id=0; A_Time offset{}, in{}, duration{}; };
struct State;
State* state=nullptr; // resident; deliberately not freed while the host may hold a refcon
int wake_host();
struct State {
    SPBasicSuite* basic=nullptr;
    const AEGP_RegisterSuite5* registration=nullptr;
    const AEGP_CommandSuite1* commands=nullptr;
    const AEGP_UtilitySuite6* utility=nullptr;
    const AEGP_LayerSuite9* layers=nullptr;
    AEGP_PluginID plugin=0;
    AEGP_Command toggle=0;
    Binding binding{};
    Dispatch dispatch{wake_host,on_main_thread};
    int registration_id=0;
    bool module_pinned=false, poisoned=false, closing=false, initialized=false;
    FILE* trace=nullptr;
    unsigned long long trace_sequence=0;
    char trace_path[384]{};
    Sample sample{};
};
int wake_host() {
    return state && state->utility ? state->utility->AEGP_CauseIdleRoutinesToBeCalled() : -1;
}
bool safe_build_id() noexcept {
    const char* p=FSTR_PROBE_BUILD_ID;
    if(!p || !*p) return false;
    size_t n=0;
    for(;p[n];++n) {
        if(n>=96) return false;
        const unsigned char c=static_cast<unsigned char>(p[n]);
        if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='-'||c=='_'||c=='.')) return false;
    }
    return true;
}
bool open_trace(State& s) noexcept {
    if(!safe_build_id()) return false;
    const int n=std::snprintf(s.trace_path,sizeof(s.trace_path),
        "/tmp/FSTRChainProbe-%ld-%s-XXXXXX",static_cast<long>(getpid()),FSTR_PROBE_BUILD_ID);
    if(n<=0 || static_cast<size_t>(n)>=sizeof(s.trace_path)) return false;
    const int fd=mkstemp(s.trace_path);
    if(fd<0) {s.trace_path[0]='\0'; return false;}
    s.trace=fdopen(fd,"w");
    if(!s.trace) {close(fd);unlink(s.trace_path);s.trace_path[0]='\0';return false;}
    return true;
}
void close_trace(State& s,bool remove_file) noexcept {
    if(s.trace) {std::fflush(s.trace);std::fclose(s.trace);s.trace=nullptr;}
    if(remove_file && s.trace_path[0]) (void)unlink(s.trace_path);
}
void write_trace(State& s,const char* text) noexcept {
    if(!s.trace || !text) return;
    char safe[512]; size_t n=0;
    for(;text[n] && n+1<sizeof(safe);++n) {
        const unsigned char c=static_cast<unsigned char>(text[n]);
        safe[n]=(c>=0x20 && c<=0x7e && c!='"' && c!='\\')?static_cast<char>(c):'_';
    }
    safe[n]='\0';
    const auto wall=std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
    if(std::fprintf(s.trace,
        "{\"schemaVersion\":1,\"buildId\":\"%s\",\"sequence\":%llu,\"wallTimeNs\":%lld,\"event\":\"%s\"}\n",
        FSTR_PROBE_BUILD_ID,++s.trace_sequence,static_cast<long long>(wall),safe)<0 ||
       std::fflush(s.trace)!=0) {
        std::fclose(s.trace);s.trace=nullptr;
    }
}
void log(State& s, const char* text) noexcept {
    if(s.utility && on_main_thread()) {
        (void)s.utility->AEGP_WriteToDebugLog("FSTRChainProbe",FSTR_PROBE_BUILD_ID,text);
        write_trace(s,text);
    }
}
template<class Suite> A_Err acquire(State& s,const char* name,A_long version,const Suite*& out) {
    const void* raw=nullptr; const A_Err err=s.basic->AcquireSuite(name,version,&raw);
    if(err) return err;
    if(!raw) return A_Err_GENERIC;
    out=static_cast<const Suite*>(raw); return A_Err_NONE;
}
void release(State& s) noexcept {
    close_trace(s,false);
    // No later callback may use SDK pointers; the inactive forwarding core remains resident.
    if(s.layers) { s.basic->ReleaseSuite(kAEGPLayerSuite,kAEGPLayerSuiteVersion9); s.layers=nullptr; }
    if(s.commands) { s.basic->ReleaseSuite(kAEGPCommandSuite,kAEGPCommandSuiteVersion1); s.commands=nullptr; }
    if(s.registration) { s.basic->ReleaseSuite(kAEGPRegisterSuite,kAEGPRegisterSuiteVersion5); s.registration=nullptr; }
    if(s.utility) { s.basic->ReleaseSuite(kAEGPUtilitySuite,kAEGPUtilitySuiteVersion6); s.utility=nullptr; }
}
void discard_before_hooks(State& s) noexcept {
    // Before the first registered host hook, no host code can retain this refcon.
    // Clean failures/no-op noninteractive loads completely instead of leaving zombie state.
    close_trace(s,true);
    release(s);
    State* owned=state;
    state=nullptr;
    delete owned;
}
A_Err read_active_layer(State& s) {
    Sample next{}; AEGP_LayerH layer=nullptr;
    A_Err err=s.layers->AEGP_GetActiveLayer(&layer);
    if(err) return err;
    if(layer) {
        next.has_layer=1;
        if((err=s.layers->AEGP_GetLayerID(layer,&next.id)) ||
           (err=s.layers->AEGP_GetLayerOffset(layer,&next.offset)) ||
           (err=s.layers->AEGP_GetLayerInPoint(layer,AEGP_LTimeMode_CompTime,&next.in)) ||
           (err=s.layers->AEGP_GetLayerDuration(layer,AEGP_LTimeMode_CompTime,&next.duration))) return err;
        if(!next.offset.scale || !next.in.scale || !next.duration.scale) return A_Err_GENERIC;
    }
    s.sample=next; // no host handle/payload escapes this synchronous read
    return A_Err_NONE;
}
void stop(State& s) noexcept {
    s.dispatch.disable();
    if(s.registration_id<=0) return;
    // A zero depth is only a local guard, NOT proof of host-wide serialization.
    // Runtime removal remains a controlled research gate, not shipping acceptance.
    if(!on_main_thread() || s.dispatch.depth.load()!=0 || s.dispatch.thread_fault.load()) {
        s.poisoned=true; log(s,"REMOVE_BLOCKED_FORWARDING_RETAINED"); return;
    }
    try {
        if(s.binding.remove(s.registration_id)==1) {s.registration_id=0; log(s,"REMOVED_OWN_ID");}
        else {s.poisoned=true; log(s,"REMOVE_UNCONFIRMED_FORWARDING_RETAINED");}
    } catch(...) {s.poisoned=true; log(s,"REMOVE_EXCEPTION_FORWARDING_RETAINED");}
}
void start(State& s) {
    if(s.poisoned || s.closing || s.registration_id!=0 || !on_main_thread()) return;
    if(!FSTR_ENABLE_PRIVATE_CHAIN_PROBE) { log(s,"BLOCKED_PRIVATE_PROBE_BUILD_OPT_IN_REQUIRED"); return; }
    const char* reason=nullptr;
    if(!s.binding.insert && !bind_loaded_ae(s.binding,reason)) {s.poisoned=true; log(s,reason); return;}
    // Pin only after exact host identity is accepted and immediately before the
    // private registry can observe our callback. Default/blocked loads stay unpinned.
    if(!s.module_pinned) {
        if(!pin_probe_module()) {s.poisoned=true; log(s,"PROBE_MODULE_PIN_FAILED_NO_RETRY"); return;}
        s.module_pinned=true;
    }
    try {
        // Refcon and module are already pinned before exposing the callback.
        const int id=s.binding.insert(Dispatch::callback,&s.dispatch);
        if(id<=0) {s.poisoned=true; log(s,"INSERT_FAILED_NO_RETRY"); return;}
        s.registration_id=id;
        s.dispatch.enable();
        log(s,"REGISTERED_RESEARCH_ONLY_SYNC001_NOT_RUN");
    } catch(...) {s.poisoned=true; s.dispatch.disable(); log(s,"INSERT_OUTCOME_UNKNOWN_NO_RETRY");}
}
A_Err command(AEGP_GlobalRefcon global,AEGP_CommandRefcon,AEGP_Command id,
              AEGP_HookPriority,A_Boolean already,A_Boolean* handled) {
    auto& s=*reinterpret_cast<State*>(global);
    if(!on_main_thread() || !s.initialized || already || id!=s.toggle || !handled) return A_Err_NONE;
    *handled=TRUE;
    if(s.registration_id>0) stop(s); else start(s);
    return A_Err_NONE;
}
A_Err menu(AEGP_GlobalRefcon global,AEGP_UpdateMenuRefcon,AEGP_WindowType) {
    auto& s=*reinterpret_cast<State*>(global);
    if(!on_main_thread() || !s.initialized || s.closing) return A_Err_NONE;
    return s.poisoned ? s.commands->AEGP_DisableCommand(s.toggle) : s.commands->AEGP_EnableCommand(s.toggle);
}
A_Err idle(AEGP_GlobalRefcon global,AEGP_IdleRefcon,A_long*) {
    auto& s=*reinterpret_cast<State*>(global);
    if(s.closing || !s.initialized || !on_main_thread()) return A_Err_NONE;
    try {
        const auto result=s.dispatch.drain([&]{return static_cast<int>(read_active_layer(s));});
        if(result==Dispatch::Drain::failed) log(s,"SNAPSHOT_FAILED_PENDING_RETAINED_NO_IDLE_RETRY");
        else if(result==Dispatch::Drain::superseded) log(s,"SNAPSHOT_SUPERSEDED_NOT_ACCEPTED");
        else if(result==Dispatch::Drain::observed) {
            char buffer[512]; const auto& v=s.sample; const auto observed=s.dispatch.observer.snapshot();
            std::snprintf(buffer,sizeof(buffer),
                "OBSERVATION_NOT_COMMIT_PROOF generation=%llu active=%d id=%ld offset=%ld/%lu in=%ld/%lu duration=%ld/%lu entered=%llu zero=%llu error=%llu unwound=%llu",
                static_cast<unsigned long long>(s.dispatch.delivered),int(v.has_layer),long(v.id),
                long(v.offset.value),static_cast<unsigned long>(v.offset.scale),long(v.in.value),
                static_cast<unsigned long>(v.in.scale),long(v.duration.value),static_cast<unsigned long>(v.duration.scale),
                static_cast<unsigned long long>(observed.entered),static_cast<unsigned long long>(observed.returned_zero),
                static_cast<unsigned long long>(observed.returned_error),static_cast<unsigned long long>(observed.unwound));
            log(s,buffer);
        }
    } catch(...) {log(s,"SNAPSHOT_EXCEPTION_PENDING_RETAINED");}
    return A_Err_NONE; // diagnostic failure must not disrupt AE idle processing
}
A_Err death(AEGP_GlobalRefcon global,AEGP_DeathRefcon) {
    auto& s=*reinterpret_cast<State*>(global);
    s.closing=true; s.dispatch.disable();
    // Do NOT mutate a possibly tearing-down private registry in an SDK death hook.
    // Stop explicitly via the command before shutdown in the isolated runtime proof.
    log(s,s.registration_id>0 ? "HOST_EXIT_FORWARDING_RETAINED" : "HOST_EXIT_NO_REGISTRATION");
    release(s); return A_Err_NONE;
}
static_assert(std::is_same_v<decltype(&command),AEGP_CommandHook>);
static_assert(std::is_same_v<decltype(&idle),AEGP_IdleHook>);
static_assert(std::is_same_v<decltype(&death),AEGP_DeathHook>);
static_assert(std::is_same_v<decltype(&menu),AEGP_UpdateMenuHook>);
} // namespace
} // namespace fstr::research

extern "C" __attribute__((visibility("default")))
A_Err EntryPointFunc(SPBasicSuite* basic,A_long major,A_long minor,AEGP_PluginID id,AEGP_GlobalRefcon* out) {
    using namespace fstr::research;
    if(!out || !basic || !basic->AcquireSuite || !basic->ReleaseSuite || state || !on_main_thread() ||
       major!=AEGP_INITFUNC_MAJOR_VERSION || minor<AEGP_INITFUNC_MINOR_VERSION) return A_Err_GENERIC;
    *out=nullptr;
    state=new(std::nothrow) State;
    if(!state) return A_Err_ALLOC;
    auto& s=*state; s.basic=basic; s.plugin=id;
    A_Err err=acquire(s,kAEGPUtilitySuite,kAEGPUtilitySuiteVersion6,s.utility);
    if(!err) err=acquire(s,kAEGPRegisterSuite,kAEGPRegisterSuiteVersion5,s.registration);
    if(!err) err=acquire(s,kAEGPCommandSuite,kAEGPCommandSuiteVersion1,s.commands);
    if(!err) err=acquire(s,kAEGPLayerSuite,kAEGPLayerSuiteVersion9,s.layers);
    if(err) {discard_before_hooks(s); return err;}
    if(!s.utility->AEGP_GetSuppressInteractiveUI || !s.utility->AEGP_CauseIdleRoutinesToBeCalled ||
       !s.utility->AEGP_WriteToDebugLog || !s.registration->AEGP_RegisterDeathHook ||
       !s.registration->AEGP_RegisterCommandHook || !s.registration->AEGP_RegisterIdleHook ||
       !s.registration->AEGP_RegisterUpdateMenuHook || !s.commands->AEGP_EnableCommand ||
       !s.commands->AEGP_DisableCommand ||
       !s.commands->AEGP_GetUniqueCommand || !s.commands->AEGP_InsertMenuCommand ||
       !s.layers->AEGP_GetActiveLayer || !s.layers->AEGP_GetLayerID || !s.layers->AEGP_GetLayerOffset ||
       !s.layers->AEGP_GetLayerInPoint || !s.layers->AEGP_GetLayerDuration) {
        discard_before_hooks(s); return A_Err_GENERIC;
    }
    A_Boolean suppressed=FALSE;
    err=s.utility->AEGP_GetSuppressInteractiveUI(&suppressed);
    if(err || suppressed) {discard_before_hooks(s); return err;}
    // The research trace is mandatory for an interactive acceptance run, but no
    // project state is read and no private callback is registered by opening it.
    if(!open_trace(s)) {discard_before_hooks(s); return A_Err_GENERIC;}
    *out=reinterpret_cast<AEGP_GlobalRefcon>(&s);
    // Once any hook is installed, keep state/code valid even on partial failure.
    err=s.registration->AEGP_RegisterDeathHook(id,death,nullptr);
    if(err) {discard_before_hooks(s); *out=nullptr; return err;}
    err=s.commands->AEGP_GetUniqueCommand(&s.toggle);
    if(!err && !s.toggle) err=A_Err_GENERIC;
    if(!err) err=s.registration->AEGP_RegisterCommandHook(id,AEGP_HP_BeforeAE,s.toggle,command,nullptr);
    if(!err) err=s.registration->AEGP_RegisterIdleHook(id,idle,nullptr);
    if(!err) err=s.registration->AEGP_RegisterUpdateMenuHook(id,menu,nullptr);
    if(!err) err=s.commands->AEGP_InsertMenuCommand(s.toggle,"FSTR Chain Probe: Start / Stop (research)",
                                                  AEGP_Menu_WINDOW,AEGP_MENU_INSERT_AT_BOTTOM);
    if(err) {s.poisoned=true; log(s,"INITIALIZATION_PARTIAL_DISABLED"); return A_Err_NONE;}
    s.initialized=true;
    log(s,"LOADED_DISABLED_BUILD_ID_IN_EVENT_TYPE_NO_PROJECT_READS");
    return A_Err_NONE;
}
static_assert(std::is_same_v<decltype(EntryPointFunc),AEGP_PluginInitFuncPrototype>);
