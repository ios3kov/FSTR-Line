#pragma once
#include "chain_abi.hpp"
#include <array>
#include <atomic>
#include <cstdint>
#include <limits>

namespace fstr::research {
// Passive, fixed-memory recording AFTER the binding is separately accepted.
// No SDK calls, payload/chain retention, I/O, allocations, wakeups or timers.
// The owner must outlive registration and ALL callbacks. This class deliberately
// does not infer registry quiescence from in_flight == 0, unregister or unload.
class Observer final {
public:
    static constexpr std::size_t message_slots = 128;
    struct Snapshot {
        std::uint64_t entered, returned_zero, returned_error, unwound;
        std::uint64_t unknown_message, in_flight;
        bool recording, overflow;
        std::array<std::uint64_t, message_slots> by_message;
    };
    Observer() noexcept {
        for (auto& count : by_message_) count.store(0, std::memory_order_relaxed);
    }
    Observer(const Observer&) = delete;
    Observer& operator=(const Observer&) = delete;
    Observer(Observer&&) = delete;
    Observer& operator=(Observer&&) = delete;

    // Toggling capture NEVER changes whether the host chain is forwarded.
    // disable() stops NEW observations, not already-entered calls. It is NOT
    // permission to delete this object, mutate the host registry or unload code.
    void enable() noexcept { recording_.store(true); }
    void disable() noexcept { recording_.store(false); }

    // Diagnostic counters only; a live snapshot is not an atomic event log or
    // an AE commit barrier. Use an externally quiescent fixture for exact totals.
    Snapshot snapshot() const noexcept {
        Snapshot out{entered_.load(), returned_zero_.load(), returned_error_.load(),
                     unwound_.load(), unknown_message_.load(), in_flight_.load(),
                     recording_.load(), overflow_.load(), {}};
        for (std::size_t i = 0; i < message_slots; ++i) out.by_message[i] = by_message_[i].load();
        return out;
    }

    // Actual candidate callback ABI: x0=chain, x1=refcon, w2=message, x3=payload.
    // Returned_zero counts a downstream return value, NOT successful delivery,
    // a successful edit, a complete transaction or a safe public-API read.
    static Result callback(Chain* chain, void* refcon, Message message, void* payload) {
        if (!refcon) return continue_chain(chain, message, payload);
        auto& self = *static_cast<Observer*>(refcon);
        InFlight flight(self);
        const bool capture = self.recording_.load();
        if (capture) {
            self.increment(self.entered_);
            if (message >= 0 && static_cast<std::size_t>(message) < message_slots)
                self.increment(self.by_message_[static_cast<std::size_t>(message)]);
            else
                self.increment(self.unknown_message_);
        }
        try {
            const Result result = continue_chain(chain, message, payload); // exactly once
            if (capture) self.increment(result == 0 ? self.returned_zero_ : self.returned_error_);
            return result; // preserve ALL bits of the host result, including negative values
        } catch (...) {
            if (capture) self.increment(self.unwound_);
            throw; // preserve exception identity; do not translate into a fake success/error
        }
    }

private:
    using Counter = std::atomic<std::uint64_t>;
    static_assert(Counter::is_always_lock_free, "Callback counters must not use hidden locks");
    static_assert(std::atomic<bool>::is_always_lock_free);
    void increment(Counter& counter) noexcept {
        if (counter.fetch_add(1) == std::numeric_limits<std::uint64_t>::max())
            overflow_.store(true); // wrapping counts cannot silently remain valid evidence
    }
    struct InFlight {
        Observer& self;
        explicit InFlight(Observer& owner) noexcept : self(owner) { self.increment(self.in_flight_); }
        ~InFlight() { self.in_flight_.fetch_sub(1); }
    };
    std::atomic<bool> recording_{false}, overflow_{false};
    Counter entered_{0}, returned_zero_{0}, returned_error_{0}, unwound_{0};
    Counter unknown_message_{0}, in_flight_{0};
    std::array<Counter, message_slots> by_message_{};
};
} // namespace fstr::research
