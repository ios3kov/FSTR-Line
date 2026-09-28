# Compatibility Matrix

Only actually tested configurations are marked as supported.

| After Effects | OS | CPU | GPU | Status |
|---|---|---|---|---|
| 22+ | macOS | Apple Silicon | not measured | Not runtime-tested yet |
| 22+ | macOS | Intel | not measured | Not runtime-tested yet |
| 22+ | Windows | x64 | not measured | Not runtime-tested yet |

## Current technical floor

The CEP manifest intentionally targets After Effects 22.0+ because FSTR Line uses persistent `Layer.id`. Adobe's integration matrix places AE 18.4+ on CEP 11 and AE 25+ on CEP 12, so CSXS 11 is the compatibility floor.

Minimum CEP runtime target: CSXS 11. This covers the AE 22+ floor while remaining loadable by newer CEP hosts.

No platform is considered supported until the clean-install AE validation gate has passed on that exact configuration.
