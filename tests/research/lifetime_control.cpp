// Owned behavioral model, NOT Adobe ABI code or proof of real AE behavior.
// Models copying a callback before unlock, then disconnecting before invocation.
#include <atomic>
#include <condition_variable>
#include <functional>
#include <iostream>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <thread>

static void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

class SignalModel {
    std::mutex mutex;
    std::function<void()> callback;
public:
    void connect(std::function<void()> value) {
        std::lock_guard<std::mutex> lock(mutex);
        callback = std::move(value);
    }
    std::function<void()> capture() {
        std::lock_guard<std::mutex> lock(mutex);
        return callback;
    }
    void disconnect() {
        std::lock_guard<std::mutex> lock(mutex);
        callback = {};
    }
};

struct Owner {
    std::atomic<int>& destroyed;
    std::mutex mutex;
    bool closed = false;
    int accepted = 0;
    explicit Owner(std::atomic<int>& count) : destroyed(count) {}
    ~Owner() { ++destroyed; }
    void close() { std::lock_guard<std::mutex> lock(mutex); closed = true; }
    void receive() {
        std::lock_guard<std::mutex> lock(mutex);
        if (!closed) ++accepted;
    }
};

static std::function<void()> guarded(const std::shared_ptr<Owner>& owner) {
    return [weak = std::weak_ptr<Owner>(owner)] {
        if (auto pinned = weak.lock()) pinned->receive();
    };
}

int main() {
    // Disconnect clears the registration, not a callback already copied out.
    SignalModel signal;
    int calls = 0;
    signal.connect([&] { ++calls; });
    auto captured = signal.capture();
    signal.disconnect();
    require(!signal.capture(), "new capture survived disconnect");
    captured();
    require(calls == 1, "fixture failed to model late delivery");

    // Native clients must not capture raw owner pointers.
    std::atomic<int> destroyed{0};
    auto owner = std::make_shared<Owner>(destroyed);
    signal.connect(guarded(owner));
    captured = signal.capture();
    signal.disconnect();
    owner.reset();
    require(destroyed == 1, "weak capture kept owner alive");
    captured(); // expired owner: no access, no use-after-free
    require(destroyed == 1, "expired callback changed lifetime");

    // A closed panel can remain alive. Weak ownership alone is insufficient.
    owner = std::make_shared<Owner>(destroyed);
    signal.connect(guarded(owner));
    captured = signal.capture();
    captured();
    require(owner->accepted == 1, "live owner did not receive");
    owner->close();
    signal.disconnect();
    captured();
    require(owner->accepted == 1, "closed owner accepted late delivery");
    owner.reset();
    require(destroyed == 2, "closed owner retained");

    // A callback which already locked the weak reference pins owner lifetime.
    // Coordinate explicitly: no sleeps, timing assumptions or AE processes.
    owner = std::make_shared<Owner>(destroyed);
    std::mutex rendezvous;
    std::condition_variable changed;
    bool pinned = false;
    bool release = false;
    signal.connect([weak = std::weak_ptr<Owner>(owner), &rendezvous, &changed,
                    &pinned, &release] {
        auto held = weak.lock();
        if (!held) return;
        std::unique_lock<std::mutex> lock(rendezvous);
        pinned = true;
        changed.notify_one();
        changed.wait(lock, [&] { return release; });
        lock.unlock();
        held->receive();
    });
    captured = signal.capture();
    std::thread running(captured);
    {
        std::unique_lock<std::mutex> lock(rendezvous);
        changed.wait(lock, [&] { return pinned; });
    }
    signal.disconnect();
    owner->close();
    owner.reset();
    const bool survived = destroyed == 2;
    {
        std::lock_guard<std::mutex> lock(rendezvous);
        release = true;
    }
    changed.notify_one();
    running.join();
    require(survived, "owner destroyed during pinned callback");
    require(destroyed == 3, "pinned owner was not eventually released");
    std::cout << "{\"kind\":\"owned-lifetime-model\",\"checks\":4,"
                 "\"result\":\"PASS\",\"aeRuntime\":\"NOT RUN\"}\n";
}
