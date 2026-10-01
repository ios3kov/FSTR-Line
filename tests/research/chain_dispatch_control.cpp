#include "dispatch.hpp"
#include <cassert>
#include <cstdio>
#include <stdexcept>
using namespace fstr::research;
namespace {
int wakes=0, wake_error=0, calls=0, result=0;
bool is_main=true, throws=false;
int wake(){++wakes;return wake_error;} bool main_thread(){return is_main;}
int next(Chain*,Message,void*) {++calls;if(throws)throw std::runtime_error("preserve");return result;}
struct Table{void* reserved[2];Continue next;} table{{nullptr,nullptr},next};
struct Context{Table* table;} context{&table};
}
int main() {
    Dispatch d(wake,main_thread);int reads=0;
    auto read=[&]{++reads;return 0;}; auto event=[&](int m=0x3b){return Dispatch::callback(&context,&d,m,reinterpret_cast<void*>(1));};
    for(int i=0;i<100;++i)d.drain(read);assert(reads==0);
    event();assert(calls==1 && wakes==0);d.enable();
    event();event();assert(wakes==1);assert(d.drain(read)==Dispatch::Drain::observed && reads==1);
    for(int i=0;i<100;++i)d.drain(read);assert(reads==1);
    event();assert(d.drain(read)==Dispatch::Drain::observed && reads==2);
    event(999);assert(d.drain(read)==Dispatch::Drain::idle);
    result=-19;assert(event()==-19);assert(d.drain(read)==Dispatch::Drain::idle);result=0;
    throws=true;try{event();assert(false);}catch(const std::runtime_error&){}throws=false;assert(d.depth==0);
    event();assert(d.drain([&]{++reads;return 5;})==Dispatch::Drain::failed);
    for(int i=0;i<100;++i)d.drain(read);assert(reads==3 && d.failed_read);
    event();assert(d.drain(read)==Dispatch::Drain::observed && reads==4);
    event();assert(d.drain([&]{++reads;event();return 0;})==Dispatch::Drain::superseded);
    assert(d.drain(read)==Dispatch::Drain::observed && reads==6);
    event();assert(d.drain([&]{assert(d.drain(read)==Dispatch::Drain::deferred);return 0;})==Dispatch::Drain::observed);
    wake_error=1;event();const auto old=wakes;event();assert(wakes==old+1 && d.wake_errors==2);
    wake_error=0;assert(d.drain(read)==Dispatch::Drain::observed);
    event();d.disable();assert(d.drain(read)==Dispatch::Drain::idle);d.enable();
    assert(d.drain(read)==Dispatch::Drain::idle); // stale pending discarded on new capture
    is_main=false;const auto before=calls;event();is_main=true;
    assert(calls==before+1 && d.thread_fault && !d.active);d.enable();assert(!d.active);
    Dispatch overflow(wake,main_thread);overflow.enable();overflow.generation.store(UINT64_MAX);
    Dispatch::callback(&context,&overflow,0x3b,nullptr);assert(overflow.overflow && !overflow.active);
    std::puts("{\"status\":\"PASS\",\"AdobeRuntime\":\"NOT RUN\",\"SYNC-001\":\"NOT RUN\"}");
}
