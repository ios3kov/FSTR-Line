// Compile against the provided Adobe headers, not invented SDK declarations.
// Surrounding host suites and BEE chain are owned fixtures, NOT an AE run.
#include "aegp_probe.cpp"
#include <cassert>
#include <cstring>
#include <stdexcept>
#include <string>
#include <vector>
using namespace fstr::research;
namespace {
AEGP_CommandHook host_command=nullptr; AEGP_IdleHook host_idle=nullptr; AEGP_DeathHook host_death=nullptr;
AEGP_GlobalRefcon global=nullptr;
Callback callback_slot=nullptr; void* callback_refcon=nullptr;
bool main_thread=true, suppressed=false, bind_ok=true, idle_fails=false;
bool layer_fails=false, invoke_nested_idle=false, throw_downstream=false;
int inserts=0, removes=0, reads=0, wakes=0, forwarded=0, released=0, bind_calls=0, downstream_result=0, wake_result=0;
std::vector<std::string> logs;
AEGP_RegisterSuite5 reg{}; AEGP_CommandSuite1 cmd{}; AEGP_UtilitySuite6 util{}; AEGP_LayerSuite9 layer{};
int insert(Callback fn,void* refcon) { ++inserts; assert(!callback_slot); callback_slot=fn;callback_refcon=refcon;return 42; }
int remove(int id) {++removes; assert(id==42); callback_slot=nullptr;return 1;}
Result next(Chain*,Message,void*) {
    ++forwarded;
    if(invoke_nested_idle) {A_long sleep=120; host_idle(global,nullptr,&sleep);assert(sleep==120);}
    if(throw_downstream) throw std::runtime_error("downstream identity");
    return downstream_result;
}
struct Table {void* unused[2]; Continue continuation;} table{{nullptr,nullptr},next};
struct ChainFixture {Table* table;} chain{&table};
void event(Message message=0x3b) {assert(callback_slot);callback_slot(&chain,callback_refcon,message,reinterpret_cast<void*>(1));}
void idle_once() {A_long sleep=120;host_idle(global,nullptr,&sleep);assert(sleep==120);}
void toggle() {A_Boolean handled=FALSE;host_command(global,nullptr,77,AEGP_HP_BeforeAE,FALSE,&handled);assert(handled);}
SPErr acquire_suite(const char* name,int32 version,const void** out) {
    if(!strcmp(name,kAEGPRegisterSuite)) {assert(version==kAEGPRegisterSuiteVersion5);*out=&reg;}
    else if(!strcmp(name,kAEGPCommandSuite)) {*out=&cmd;}
    else if(!strcmp(name,kAEGPUtilitySuite)) {*out=&util;}
    else if(!strcmp(name,kAEGPLayerSuite)) {*out=&layer;}
    else return 1;
    return 0;
}
void setup() {
    reg.AEGP_RegisterCommandHook=[](AEGP_PluginID,AEGP_HookPriority,AEGP_Command id,AEGP_CommandHook fn,AEGP_CommandRefcon) -> A_Err {assert(id==77);host_command=fn;return A_Err_NONE;};
    reg.AEGP_RegisterIdleHook=[](AEGP_PluginID,AEGP_IdleHook fn,AEGP_IdleRefcon) -> A_Err {if(idle_fails)return A_Err_GENERIC;host_idle=fn;return A_Err_NONE;};
    reg.AEGP_RegisterDeathHook=[](AEGP_PluginID,AEGP_DeathHook fn,AEGP_DeathRefcon) -> A_Err {host_death=fn;return A_Err_NONE;};
    reg.AEGP_RegisterUpdateMenuHook=[](AEGP_PluginID,AEGP_UpdateMenuHook,AEGP_UpdateMenuRefcon) -> A_Err {return A_Err_NONE;};
    cmd.AEGP_EnableCommand=[](AEGP_Command) -> A_Err {return A_Err_NONE;};
    cmd.AEGP_DisableCommand=[](AEGP_Command) -> A_Err {return A_Err_NONE;};
    cmd.AEGP_GetUniqueCommand=[](AEGP_Command* id) -> A_Err {*id=77;return A_Err_NONE;};
    cmd.AEGP_InsertMenuCommand=[](AEGP_Command,const A_char*,AEGP_MenuID,A_long) -> A_Err {return A_Err_NONE;};
    util.AEGP_GetSuppressInteractiveUI=[](A_Boolean* value) -> A_Err {*value=suppressed;return A_Err_NONE;};
    util.AEGP_WriteToDebugLog=[](const A_char*,const A_char* build,const A_char* text) -> A_Err {assert(strstr(build,"sdk-control"));logs.emplace_back(text);return A_Err_NONE;};
    util.AEGP_CauseIdleRoutinesToBeCalled=[]() -> A_Err {++wakes;return static_cast<A_Err>(wake_result);};
    layer.AEGP_GetActiveLayer=[](AEGP_LayerH* out) -> A_Err {++reads;if(layer_fails)return A_Err_GENERIC;*out=reinterpret_cast<AEGP_LayerH>(1);return A_Err_NONE;};
    layer.AEGP_GetLayerID=[](AEGP_LayerH,AEGP_LayerIDVal* out) -> A_Err {*out=12;return A_Err_NONE;};
    layer.AEGP_GetLayerOffset=[](AEGP_LayerH,A_Time* out) -> A_Err {*out={2,24};return A_Err_NONE;};
    layer.AEGP_GetLayerInPoint=[](AEGP_LayerH,AEGP_LTimeMode mode,A_Time* out) -> A_Err {assert(mode==AEGP_LTimeMode_CompTime);*out={3,24};return A_Err_NONE;};
    layer.AEGP_GetLayerDuration=[](AEGP_LayerH,AEGP_LTimeMode,A_Time* out) -> A_Err {*out={60,24};return A_Err_NONE;};
}
}
namespace fstr::research {
bool on_main_thread() noexcept {return main_thread;}
bool pin_probe_module() noexcept {return true;} // only the binding is substituted
bool bind_loaded_ae(Binding& out,const char*& reason) noexcept {
    ++bind_calls;reason="FIXTURE_REFUSED";if(!bind_ok)return false;
    out={insert,remove};return true;
}
}
int main(int argc,char** argv) {
    assert(argc==2); const std::string scenario=argv[1]; setup();
    suppressed=scenario=="suppressed";idle_fails=scenario=="partial";bind_ok=scenario!="wrong-host";
    SPBasicSuite basic{};basic.AcquireSuite=acquire_suite;
    basic.ReleaseSuite=[](const char*,int32) -> A_Err {++released;return SPErr(0);};
    assert(EntryPointFunc(&basic,1,9,123,&global)==A_Err_NONE);
    if(suppressed) {assert(!global && !host_command && !inserts && released==4);}
    else if(idle_fails) {
        A_Boolean handled=FALSE;host_command(global,nullptr,77,AEGP_HP_BeforeAE,FALSE,&handled);
        assert(!handled && !inserts);host_death(global,nullptr);assert(released==4);
    } else {
        for(int i=0;i<20;++i) idle_once(); assert(reads==0 && inserts==0 && wakes==0);
        toggle();
        if(scenario=="disabled") {assert(!inserts && !bind_calls);host_death(global,nullptr);}
        else if(scenario=="wrong-host") {assert(!inserts && bind_calls==1);toggle();assert(bind_calls==1);host_death(global,nullptr);}
        else {
            assert(inserts==1);event();event();assert(wakes==1 && reads==0 && forwarded==2);
            idle_once();assert(reads==1 && state->dispatch.delivered==2);
            for(int i=0;i<20;++i)idle_once();assert(reads==1);
            event();idle_once();assert(reads==2 && state->dispatch.delivered==3);
            event(999);idle_once();assert(reads==2);
            downstream_result=-7;event();idle_once();assert(reads==2);downstream_result=0;
            throw_downstream=true;try {event();assert(false);}catch(const std::runtime_error& e){assert(!strcmp(e.what(),"downstream identity"));}
            throw_downstream=false;assert(state->dispatch.depth.load()==0);
            invoke_nested_idle=true;event();invoke_nested_idle=false;assert(reads==2);idle_once();assert(reads==3);
            layer_fails=true;event();idle_once();assert(reads==4 && state->dispatch.failed_read);
            for(int i=0;i<20;++i)idle_once();assert(reads==4); // no blind retry/polling
            layer_fails=false;event();idle_once();assert(reads==5);
            wake_result=17;event();assert(state->dispatch.wake_errors.load()==1);idle_once();assert(reads==6);wake_result=0;
            if(scenario=="wrong-thread") {
                main_thread=false;event();main_thread=true;assert(state->dispatch.thread_fault.load());
                toggle();assert(removes==0 && callback_slot);host_death(global,nullptr);
                const auto before=forwarded;event();assert(forwarded==before+1 && released==4);
            } else {
                const auto escaped=callback_slot;void* escaped_refcon=callback_refcon;
                toggle();assert(removes==1 && !callback_slot);
                const auto before=forwarded;escaped(&chain,escaped_refcon,0x3b,reinterpret_cast<void*>(1));
                assert(forwarded==before+1);idle_once();assert(reads==6);
                host_death(global,nullptr);assert(released==4);
            }
        }
    }
    std::printf("{\"status\":\"PASS\",\"scenario\":\"%s\",\"AdobeRuntime\":\"NOT RUN\"}\n",argv[1]);
}
