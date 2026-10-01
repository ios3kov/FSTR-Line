// Owned ABI-shaped chain only. No Adobe SDK, libraries, process or debugger.
#include "observer.hpp"
#include <atomic>
#include <climits>
#include <condition_variable>
#include <cstdlib>
#include <iostream>
#include <mutex>
#include <new>
#include <stdexcept>
#include <thread>
#include <vector>
#include <sys/mman.h>
#include <unistd.h>
using namespace fstr::research;

static std::atomic<unsigned long> allocations{0};
void* operator new(std::size_t n) {
    allocations.fetch_add(1);
    if (void* p = std::malloc(n ? n : 1)) return p;
    throw std::bad_alloc();
}
void* operator new[](std::size_t n) { return ::operator new(n); }
void operator delete(void* p) noexcept { std::free(p); }
void operator delete[](void* p) noexcept { std::free(p); }
void operator delete(void* p, std::size_t) noexcept { std::free(p); }
void operator delete[](void* p, std::size_t) noexcept { std::free(p); }
#define CHECK(x) do { if (!(x)) throw std::runtime_error(#x); } while (false)

struct Host;
struct Iterator {
    Continue* table;
    Host* host;
    std::size_t cursor;
};
struct Node { int id; Callback function; void* refcon; };
struct Host {
    // This registry is deliberately SERIALIZED; it does not model AE thread safety.
    std::vector<Node> nodes;
    int next_id = 1;
    unsigned depth = 0;
    unsigned terminal_calls = 0;
    int result = 0;
    void* expected_payload = nullptr;
    Message expected_message = 0;
    bool verify_arguments = true;
    int insert(Callback cb, void* refcon) {
        CHECK(depth == 0);
        const int id = next_id++;
        nodes.insert(nodes.begin(), {id, cb, refcon});
        return id;
    }
    bool remove(int id) {
        CHECK(depth == 0); // owned host boundary; zero Observer count is NOT the authority
        for (auto it = nodes.begin(); it != nodes.end(); ++it)
            if (it->id == id) { nodes.erase(it); return true; }
        return false;
    }
    static int next(Chain* raw, Message message, void* payload) {
        auto& it = *static_cast<Iterator*>(raw);
        auto& host = *it.host;
        if (it.cursor < host.nodes.size()) {
            const auto node = host.nodes[it.cursor++];
            return node.function(raw, node.refcon, message, payload);
        }
        if (host.verify_arguments) {
            CHECK(message == host.expected_message);
            CHECK(payload == host.expected_payload);
        }
        ++host.terminal_calls;
        return host.result;
    }
    int dispatch(Message message, void* payload = nullptr) {
        static Continue table[3] = {nullptr, nullptr, &Host::next};
        Iterator chain{table, this, 0};
        struct Depth { Host& h; explicit Depth(Host& x):h(x){++h.depth;} ~Depth(){--h.depth;} } guard(*this);
        return next(&chain, message, payload);
    }
};

static void repeated_and_results() {
    Host host; Observer observer; observer.enable();
    host.insert(&Observer::callback, &observer);
    int value = 12; host.expected_payload = &value; host.expected_message = 0x3b;
    for (int result : {0, 9, -9, INT_MIN, INT_MAX}) {
        host.result = result;
        CHECK(host.dispatch(0x3b, &value) == result);
    }
    auto s = observer.snapshot();
    CHECK(host.terminal_calls == 5 && s.entered == 5 && s.by_message[0x3b] == 5);
    CHECK(s.returned_zero == 1 && s.returned_error == 4 && s.unwound == 0 && s.in_flight == 0);
}
static void inactive_and_null_refcon() {
    Host host; Observer observer;
    const int id = host.insert(&Observer::callback, &observer);
    CHECK(host.dispatch(0) == 0 && observer.snapshot().entered == 0);
    observer.enable(); CHECK(host.dispatch(0) == 0);
    observer.disable(); CHECK(host.dispatch(0) == 0);
    CHECK(host.terminal_calls == 3 && observer.snapshot().entered == 1);
    CHECK(host.remove(id));
    host.insert(&Observer::callback, nullptr);
    CHECK(host.dispatch(0) == 0 && host.terminal_calls == 4);
}
static void real_fixture_removal_preserves_others() {
    Host host; Observer first, second; first.enable(); second.enable();
    const int first_id = host.insert(&Observer::callback, &first);
    const int our_id = host.insert(&Observer::callback, &second);
    CHECK(host.dispatch(0) == 0);
    second.disable(); CHECK(host.dispatch(0) == 0); // still forwards while registered
    CHECK(host.remove(our_id) && !host.remove(our_id));
    CHECK(host.dispatch(0) == 0);
    CHECK(first.snapshot().entered == 3 && second.snapshot().entered == 1);
    CHECK(host.nodes.size() == 1 && host.nodes.front().id == first_id);
    CHECK(host.terminal_calls == 3);
}
static int throw_same_pointer(Chain*, void* refcon, Message, void*) { throw refcon; }
static void exception_identity() {
    Host host; Observer observer; observer.enable(); int sentinel = 3;
    host.insert(&throw_same_pointer, &sentinel);
    host.insert(&Observer::callback, &observer);
    bool caught = false;
    try { host.dispatch(0); } catch (void* p) { CHECK(p == &sentinel); caught = true; }
    auto s = observer.snapshot();
    CHECK(caught && s.entered == 1 && s.unwound == 1 && s.in_flight == 0);
    CHECK(s.returned_zero == 0 && s.returned_error == 0 && host.depth == 0);
}
struct Nested { Host* host; Observer* observer; bool nesting = false; unsigned max_in_flight = 0; };
static int reenter(Chain* chain, void* refcon, Message message, void* payload) {
    auto& state = *static_cast<Nested*>(refcon);
    const auto now = static_cast<unsigned>(state.observer->snapshot().in_flight);
    if (now > state.max_in_flight) state.max_in_flight = now;
    if (!state.nesting) {
        state.nesting = true;
        CHECK(state.host->dispatch(message, payload) == 0);
        state.nesting = false;
    }
    return continue_chain(chain, message, payload);
}
static void nested_dispatch() {
    Host host; Observer observer; observer.enable(); Nested nested{&host, &observer};
    host.insert(&reenter, &nested); host.insert(&Observer::callback, &observer);
    CHECK(host.dispatch(0) == 0);
    CHECK(nested.max_in_flight == 2 && host.terminal_calls == 2);
    auto s = observer.snapshot(); CHECK(s.entered == 2 && s.returned_zero == 2 && s.in_flight == 0);
}
static void unknown_and_unreadable_payload() {
    Host host; Observer observer; observer.enable(); host.insert(&Observer::callback, &observer);
    const auto bytes = static_cast<std::size_t>(sysconf(_SC_PAGESIZE));
    void* payload = mmap(nullptr, bytes, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    CHECK(payload != MAP_FAILED); host.expected_payload = payload;
    for (int message : {-1, INT_MIN, 128, INT_MAX}) {
        host.expected_message = message; CHECK(host.dispatch(message, payload) == 0);
    }
    CHECK(munmap(payload, bytes) == 0);
    auto s = observer.snapshot(); CHECK(s.unknown_message == 4 && s.entered == 4);
    for (auto n : s.by_message) CHECK(n == 0);
}
static void no_heap_on_normal_callback_path() {
    Host host; Observer observer; observer.enable(); host.insert(&Observer::callback, &observer);
    const auto before = allocations.load();
    for (int i = 0; i < 10000; ++i) CHECK(host.dispatch(0) == 0);
    CHECK(allocations.load() == before);
    CHECK(observer.snapshot().entered == 10000 && host.terminal_calls == 10000);
}
struct Rendezvous { std::mutex mutex; std::condition_variable condition; bool entered = false, release = false; };
static int wait_downstream(Chain* chain, void* refcon, Message message, void* payload) {
    auto& sync = *static_cast<Rendezvous*>(refcon);
    { std::unique_lock<std::mutex> lock(sync.mutex);
      sync.entered = true; sync.condition.notify_one();
      sync.condition.wait(lock, [&]{return sync.release;}); }
    return continue_chain(chain, message, payload);
}
static void disable_during_inflight() {
    Host host; Observer observer; observer.enable(); Rendezvous sync;
    host.insert(&wait_downstream, &sync); const int own_id = host.insert(&Observer::callback, &observer);
    std::thread worker([&] { CHECK(host.dispatch(0) == 0); });
    { std::unique_lock<std::mutex> lock(sync.mutex); sync.condition.wait(lock, [&]{return sync.entered;}); }
    observer.disable(); CHECK(observer.snapshot().in_flight == 1);
    // Do not call remove/delete here. The host has not reached a quiescent boundary.
    { std::lock_guard<std::mutex> lock(sync.mutex); sync.release = true; sync.condition.notify_one(); }
    worker.join();
    auto s = observer.snapshot(); CHECK(s.in_flight == 0 && s.entered == 1 && s.returned_zero == 1);
    CHECK(host.remove(own_id)); // worker joined; fixture owner established actual quiescence
    CHECK(host.dispatch(0) == 0 && host.terminal_calls == 2);
}
static void independent_concurrent_chains() {
    Observer observer; observer.enable(); std::vector<std::thread> threads;
    for (int i = 0; i < 4; ++i) threads.emplace_back([&] {
        Host own_host; own_host.insert(&Observer::callback, &observer);
        for (int j = 0; j < 1000; ++j) CHECK(own_host.dispatch(0) == 0);
    });
    for (auto& t : threads) t.join();
    auto s = observer.snapshot();
    CHECK(s.entered == 4000 && s.returned_zero == 4000 && s.by_message[0] == 4000 && s.in_flight == 0);
}
static void all_message_bins() {
    Host host; Observer observer; observer.enable(); host.insert(&Observer::callback, &observer);
    for (int i = 0; i < 128; ++i) { host.expected_message = i; CHECK(host.dispatch(i) == 0); }
    auto s = observer.snapshot();
    CHECK(s.entered == 128 && s.unknown_message == 0 && !s.overflow);
    for (auto n : s.by_message) CHECK(n == 1);
}
int main() {
    try {
        repeated_and_results(); inactive_and_null_refcon(); real_fixture_removal_preserves_others();
        exception_identity(); nested_dispatch(); unknown_and_unreadable_payload();
        no_heap_on_normal_callback_path(); disable_during_inflight();
        independent_concurrent_chains(); all_message_bins();
        std::cout << "{\"status\":\"PASS\",\"scenarios\":10,\"scope\":\"actual core on owned ABI-shaped chain\","
                     "\"AdobeRuntime\":\"NOT RUN\",\"SYNC-001\":\"NOT RUN\"}\n";
        return 0;
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
