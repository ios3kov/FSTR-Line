# Native subscription lifetime research — 2026-09-29

Scope: static arm64 inspection of AE 25.6.0.101 plus an owned C++17 model.
No Adobe library loaded by the model, no private function invoked, no running
AE attached or modified. This is not shipping-path acceptance.

## Static evidence

Files under the installed AE 2025 application's Contents/Frameworks:

| Binary | SHA-256 |
| --- | --- |
| BEE.dylib | `817b9de9c6d57b5d6988b634842090e1528fe817a5685c8d1ff358553c6660ca` |
| AfterFXLib.framework/Versions/A/AfterFXLib | `ce3aa2f16fe5449a77379a6b622e1a221596e511b86f7708dd3e2f7a3cced01a` |
| dvacore.framework/Versions/A/dvacore | `cb6faaf5b745903b80b44105b658ab68186d5065ae47c8a57c9b23e26aa8ecb0` |

Inspection used `xcrun nm -arch arm64` and bounded symbol disassembly with
`xcrun llvm-objdump --macho --arch=arm64 --disassemble --dis-symname SYMBOL`.
Addresses below are unslid disassembly addresses, not runtime pointers.

| Location | Observed behavior |
| --- | --- |
| BEE dirty signal emitter, `0x3a4b90` | Copies callback shared ownership at `0x3a4c54`, unlocks link mutex at `0x3a4c6c`, unlocks signal mutex at `0x3a4c78`, then invokes callback at `0x3a4ca8` |
| BEE dirty signal ConnectionLinkImpl::Disconnect, `0x3b09a4` | Locks link mutex at `0x3b09c0`, clears registered callback pair at `0x3b09c8`, releases ownership and unlocks |
| dvacore ScopedConnection destructor, `0x182ab8` | Calls Disconnect at `0x182ad4`, then releases weak control ownership |
| AfterFXLib CProject::SetDirtyFunc, `0xaab5c4` | Acquires shared project ownership, calls ConnectDirtyStateChangedSignal at `0xaab760`, moves connection to scoped member at project offset `0x250` |
| AfterFXLib native callback thunk, `0xac51bc` | Locks weak owner at `0xac51e4`, skips expired owner, invokes owner's callback at `0xac5218`, then releases strong reference |
| AfterFXLib CProject destructor, `0xaabd04` | Destroys scoped connection at `0xaabe00` before callback storage teardown at `0xaabe30` |

Inference: a callback copied before disconnect can remain independently alive
and be invoked after the registration is cleared. Disconnect alone is **not
evidence of callback quiescence**. This is a static lifetime conclusion, not an
observed race in real AE. Native weak-owner capture avoids a raw-owner lifetime
assumption; it does not establish safety of unloading callback machine code.

A narrow direct-call scan located CProject::SetDirtyFunc and an Undo-completed
getter in SamuraiUpdateParamsUI. No direct `bl` producer call to
BroadcastDirtyState was found. Indirect calls and tail branches are not covered
by that scan; absence of a match does not prove absence of production events.

## Reproducible owned control

`tests/research/test_lifetime_control.py` compiles `lifetime_control.cpp` in a
unique temporary directory and executes it with compile/run timeouts. Four
deterministic checks cover copied callback after disconnect, expired weak owner,
closed-but-live owner, and an already-running callback pinning owner lifetime.
The concurrent case uses condition-variable rendezvous, not sleeps.

On macOS arm64 the test passed with AddressSanitizer and UndefinedBehaviorSanitizer:

```sh
FSTR_LIFETIME_SANITIZERS=1 python3 -B -m unittest discover -s tests/research -p test_lifetime_control.py -v
```

Output explicitly records `aeRuntime: NOT RUN`. The existing research test
discovery includes this control on CI. A model PASS does not validate private
Adobe ABI, actual callback threads, real event coverage or module unload.

## Decision and remaining gates

Any future native adapter must account for copied/in-flight callbacks, weak or
equivalent safe owner acquisition, a closed/generation gate, and separately
proven callback drainage before module unload. Do not instantiate guessed
private classes or integrate this research model into the product.

Next: establish producer registration and repeated-dirty emission semantics,
then safe project acquisition and full ABI in a disposable native harness.
Shipping source, post-commit behavior, mismatch recovery, event coverage,
uninstrumented performance and compatibility/licensing/maintenance remain
BLOCKED or NOT RUN. No production gate is closed by this record.
