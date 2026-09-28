# Compatibility Matrix

Only actually tested configurations are marked as supported.

| After Effects | OS | CPU | GPU | Status |
|---|---|---|---|---|
| 22+ | macOS | Apple Silicon | not measured | Not runtime-tested yet |
| 22+ | macOS | Intel | not measured | Not runtime-tested yet |
| 22+ | Windows | x64 | not measured | Not runtime-tested yet |

## Current technical floor

The CEP manifest intentionally targets After Effects 22.0+ because FSTR Line uses persistent `Layer.id`.

CEP runtime target: CSXS 12.

No platform is considered supported until the clean-install AE validation gate has passed on that exact configuration.
