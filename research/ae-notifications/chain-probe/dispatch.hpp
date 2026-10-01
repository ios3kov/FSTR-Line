#pragma once
#include "observer.hpp"

namespace fstr::research {
// Only the source callback creates pending work. Idle never discovers changes.
// The owner, wake function and thread predicate stay alive for the registration.
class Dispatch final {
public:
    using Wake = int (*)();
    using MainThread = bool (*)();
    enum class Drain { idle, deferred, observed, failed, superseded };
    Dispatch(Wake wake, MainThread main) noexcept : wake_(wake), main_(main) {}
    Dispatch(const Dispatch&) = delete;
    Dispatch& operator=(const Dispatch&) = delete;
    Observer observer;
    std::atomic<bool> active{false}, thread_fault{false}, overflow{false};
    std::atomic<std::uint64_t> generation{0}, wake_errors{0}, depth{0};
    std::uint64_t delivered = 0, attempted = 0; // owner/main thread only
    bool failed_read = false;

    // Called only by the serialized owner, outside callbacks/drain.
    void enable() noexcept {
        delivered=attempted=generation.load(); failed_read=false;
        wake_pending_.store(false);
        if(thread_fault.load() || overflow.load()) return;
        observer.enable(); active.store(true);
    }
    void disable() noexcept { active.store(false); observer.disable(); }
    static bool relevant(Message m) noexcept {
        switch (m) {
            case 0x1a: case 0x1b: case 0x3b: case 0x54: case 0x55:
            case 0x57: case 0x59: case 0x5a: case 0x5b: case 0x5f: return true;
            default: return false; // narrow proof, NOT complete SYNC-001 coverage
        }
    }
    static Result callback(Chain* chain, void* refcon, Message message, void* payload) {
        auto& self = *static_cast<Dispatch*>(refcon);
        struct Scope {
            Dispatch& self;
            explicit Scope(Dispatch& s) : self(s) { self.depth.fetch_add(1); }
            ~Scope() { self.depth.fetch_sub(1); }
        } scope(self);
        // Always forward, including disabled/unknown/error/exception paths.
        const Result result = Observer::callback(chain, &self.observer, message, payload);
        if (self.active.load() && relevant(message)) {
            if (!self.main_()) { self.thread_fault.store(true); self.disable(); }
            else if (result == 0) {
                if (self.generation.fetch_add(1) == UINT64_MAX) {
                    self.overflow.store(true); self.disable();
                } else if (!self.wake_pending_.exchange(true) && self.wake_() != 0) {
                    self.wake_errors.fetch_add(1); // pending retained; no recursive retry
                    self.wake_pending_.store(false); // another REAL event may request again
                }
            }
        }
        return result;
    }
    // read() uses only fresh public handles. A successful read is an observation,
    // NOT proof of producer provenance, complete delivery or transaction commit.
    template<class Reader> Drain drain(Reader read) {
        if (!main_() || !active.load() || thread_fault.load() || overflow.load()) return Drain::idle;
        if (draining_ || depth.load() != 0) return Drain::deferred;
        const auto ticket = generation.load();
        if (ticket == delivered || (failed_read && ticket == attempted)) return Drain::idle;
        struct Scope { bool& value; explicit Scope(bool& v): value(v) { value=true; }
                       ~Scope() { value=false; } } scope(draining_);
        wake_pending_.store(false);
        attempted = ticket;
        int result = -1;
        try { result = read(); } catch (...) { failed_read=true; throw; }
        if (result != 0) { failed_read=true; return Drain::failed; }
        failed_read=false;
        // A callback during read means the result must NOT be published as stable.
        if (generation.load() != ticket || !active.load()) return Drain::superseded;
        delivered=ticket;
        return Drain::observed;
    }
private:
    Wake const wake_;
    MainThread const main_;
    std::atomic<bool> wake_pending_{false};
    bool draining_ = false; // main-thread guard
};
} // namespace fstr::research
