# Native callback-chain probe core (not an AE plugin)

This is the first **implemented** part of the `BEE_Callback_Insert/Remove`
probe, following `docs/TEST_RECORDS/BEE-CALLBACK-SOURCE-2026-09-30.md`.
It has no AEGP entry point, dynamic loader, installer, timer, host-state reader
or mechanism to attach to an Adobe process. Nothing here activates on AE startup.

`Observer::callback` uses the inspected four-argument ABI and forwards exactly
once through the supplied chain's third virtual slot. It preserves integer
results and C++ exception identity. No Adobe class/layout is instantiated.
Only the vptr and the inspected Continue slot are read; chain/payload pointers
are not stored or dereferenced as project, layer or AEGP objects. A null refcon
still forwards. A null/invalid chain is **not** an accepted input.

Recording is opt-in, bounded to fixed counters (128 numeric message bins and
one unknown bin), lock-free on supported compilation targets, with no heap
allocation or I/O on the ordinary callback path. Exception creation belongs to
the downstream fixture/host, not the observer. Counters are cumulative. Disabled
recording still forwards; disabling mid-call allows that already-entered
observation to finish. Result 0 is NOT called successful notification delivery.

## Lifetime boundary — not solved by an atomic counter

Keep the callback code and its `Observer` refcon alive until removal AND actual
host quiescence are established. `disable()` is **logical deactivation**, not
unsubscription. `snapshot().in_flight == 0` is NOT proof that no new callback can
start; snapshots during activity are not a coherent event log. This increment
intentionally has no generic destructor that calls Remove or unloads anything.

The test host owns a serialized registry and proves it is quiescent before
removing **only its own** subscription ID. That checks callback/core behavior,
not the actual BEE registry's thread affinity or removal contract. Do not use
its fake registry as an Adobe ABI implementation.

## Run the implemented core

From a checkout, run:

```sh
python3 -B -m unittest discover -s tests/research -p test_chain_probe.py -v
```

The test compiles and executes the actual callback against an owned C++ chain,
including repeated changes, nested dispatch, errors/unwinding, logical disable,
true fixture removal, and concurrent *independent* chains sharing counters.
ASan/UBSan and optimized builds run separately; neither loads Adobe libraries.
The arm64 shim is also compiled to ARM64 assembly without SDK headers and its
lowered forwarding instructions are checked. This is ABI-code-generation
evidence, not evidence that a real AE invocation was safe.

## Remaining AEGP proof, SDK and activation gates

A matching Adobe SDK archive has not been supplied to this working runtime.
Do not invent SDK declarations or label this core as a built `.plugin`.
Next: use those real headers to compile the AEGP host boundary, and bind only
an already-loaded exact AE 25.6.0.101 arm64 BEE image. Before enabling, verify
module identity and loaded code/UUID, exact Insert/Remove exports and Continue
contract; reject other builds, architectures and unresolved bindings.
Registration/removal must happen at a proven serialized host boundary. Keep
observation/state resident and forwarding intact until that is established.

Then run the disposable-project gate without LLDB: two native layer-time edits
without saving, script edits, selection/reorder, Undo/Redo, project close/switch,
logical disable and actual removal, downstream errors and competing filters.
Any later AEGP idle dispatch is event-driven transport ONLY, not a polling
source. These counters alone do not establish post-commit reads or SYNC-001.

**AE load/build/run, real native subscription and SYNC-001: NOT RUN/BLOCKED.**
