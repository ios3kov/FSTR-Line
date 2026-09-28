# Compatibility Matrix

Only real runtime-tested configurations are marked verified/supported.

| Configuration | Verified Build ID | Scope | Date | Result | Known limitations |
|---|---|---|---|---|---|
| AE 22+ / macOS / Apple Silicon | — | Not run | — | untested | real AE runtime unavailable in current tool environment |
| AE 22+ / macOS / Intel | — | Not run | — | untested | real AE runtime unavailable in current tool environment |
| AE 22+ / Windows x64 | — | Not run | — | untested | real AE runtime unavailable in current tool environment |

## Current technical floor

The CEP manifest targets After Effects 22.0+ because FSTR Line uses persistent Layer.id.

Minimum CEP runtime target: CSXS 11. Actual compatibility is not claimed until tested.

## Automated validation launchers

- macOS runner: launches a clean AE instance through JXA and executes the unique test wrapper.
- Windows runner: launches AfterFX.exe with -r and the unique wrapper path.
- Before launch, the runner validates the exact installed CEP file set and hashes.
- Inside AE, the smoke requires the loaded host Build ID and Git commit to match the installed artifact.
- Every invocation has a unique Test Run ID and structured Evidence record.

Launcher implementation/tests do not mark a platform supported by themselves. A real successful run on the specific configuration is required.
