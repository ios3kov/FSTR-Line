# BEE chain research probe — not a shipping plugin

Target candidate: exactly AE 25.6.0.101, macOS arm64 (not arm64e/Intel).
The uploaded SDK is an external build input, never part of this repository.
No installable artifact or real-AE acceptance is supplied by this increment.

## Implemented

- `observer.hpp` and `chain_abi.hpp`: previously tested transparent forwarding core, unchanged.
- `dispatch.hpp`: real source callbacks produce pending generations; a cached wake
  requests host idle delivery. Idle without an event performs no project read.
  Failed reads keep pending but are not retried on every idle; another real event
  permits another attempt. Nested/overlapping observations are not published as stable.
- `aegp_probe.cpp`: actual SDK entry/hook declarations, own Start/Stop menu command,
  noninteractive refusal, event-triggered fresh active-layer timing reads and
  debug-log observations. Interactive research loads also create a private 0600
  `/tmp/FSTRChainProbe-<pid>-<buildId>-*` JSONL trace for no-LLDB acceptance.
  Trace I/O happens only on the main-thread AEGP path, never inside the BEE callback.
  It never mutates/saves/closes a project. Callback payloads are neither dereferenced
  nor retained as handles.
- `binding_macos.cpp`: only already-loaded expected libraries, exact bundle version,
  file SHA, loaded UUID/header/text comparison and export-owner validation.
  No absent Adobe library load, absolute text address call or arbitrary CLI override.
- `build_probe.py` / `Probe_PiPL.r`: clean-source macOS bundle build recipe, PiPL,
  explicit runtime Build ID, ad-hoc signature verification and external build record.

The active-layer snapshot is intentionally narrow. Multiple/no selected layers,
all Timeline fields/origins, true project identity and post-commit completeness
are NOT accepted by this sample. Numeric event mappings remain research evidence.

## Lifecycle limits

Recording is off at load. Default builds also refuse private registration entirely.
Opening the diagnostic trace does not read project state or register the private
callback; pre-hook failures remove their trace. A clean host death retains a bounded
trace as runtime evidence. Trace failure blocks the interactive research helper
rather than silently producing unverifiable acceptance evidence.
The research opt-in is not permission to deploy this code in a user's working AE.
Use only after the isolated runtime protocol and applicable gates are satisfied.
All chain callbacks continue exactly once, preserving the downstream result and
exceptions. Unsupported callback threads disable observation, not forwarding.
Registration/removal must occur outside dispatch on the host thread; a zero local
in-flight count does not prove host-wide serialization or callback quiescence.
An unknown insertion/removal outcome blocks retries. The AEGP module, successful
image binding and refcon stay resident. The SDK death hook disables observation
but does not mutate the possibly tearing-down private registry. Explicit Stop is
part of the future isolated test. Residency is not a full lifetime-safety proof.

## Build and controls

On an authorized Apple Silicon Mac, with a clean checkout and external SDK:

```sh
python3 -B research/ae-notifications/chain-probe/build_probe.py --sdk /path/to/ae25.6_61.64bit.AfterEffectsSDK
```

This produces a **private-registration-disabled** bundle, not runtime acceptance.
`--research-opt-in` is a separate unaccepted research build configuration. Neither
configuration is installed or launched by the script. The output record keeps
`handoffApproved=false`, `AEGP_load=NOT RUN` and `SYNC-001=NOT RUN`.

```sh
FSTR_AE_SDK_ROOT=/path/to/ae25.6_61.64bit.AfterEffectsSDK \
python3 -B -m unittest discover -s tests/research -p test_chain_aegp.py -v
```


### No-LLDB evidence validation

The trace parser is fail-closed and does not launch AE. Disabled mode proves only
that the helper loaded with the expected Build ID and never registered the private
callback. Active mode additionally requires registration, ordered stable reads,
own-ID removal and clean exit.

For a controlled repeated-edit/Undo/Redo run, bind the trace to an exact expected
active-layer state sequence:

```json
{
  "schemaVersion": 1,
  "kind": "FSTRChainProbeExpectedStates",
  "buildId": "fstr-chain-aegp-<commit>-research-opt-in",
  "states": [
    {"label":"edit-1","id":12,"offset":[2,24],"in":[3,24],"duration":[60,24]},
    {"label":"edit-2","id":12,"offset":[4,24],"in":[5,24],"duration":[60,24]}
  ]
}
```

```sh
python3 -B research/ae-notifications/chain-probe/trace_acceptance.py \
  --trace /tmp/FSTRChainProbe-... \
  --build-id fstr-chain-aegp-<commit>-research-opt-in \
  --mode active \
  --expected-states /path/to/expected-states.json
```

This requires the exact number and order of stable observations to match the plan
and rejects snapshot-read failures. It still does **not** prove action origin
(native UI vs script vs Undo/Redo) by itself; origin needs independent controlled
ground truth from the real-AE run. It is partial runtime evidence, never a full
SYNC-001 PASS.

On Linux the SDK control uses the supplied header's own Android conditional branch;
this tests C++ implementation/declarations, **not macOS SDK ABI or Android host support**.
The loader test needs macOS and no Adobe SDK. Missing inputs are reported as skipped,
not successful native builds. The existing LLDB #3 failures remain separate and open.
