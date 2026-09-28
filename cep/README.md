# CEP developer prototype

Current integration branch: read-only visual tracks on the canonical typed Core/HostAdapter. It is not a release and editing UI is intentionally gated on real AE acceptance. Main and donor PR #1 are not merged by this work.

## Level 1 gate

Run from an exact clean Git checkout with Node 22+, Python 3.10+ and a C++17 compiler:

```sh
npm ci
npm test
npm run check:cep
node --test tests/runtime/*.test.mjs
python3 -B -m unittest discover -s tests/research -p 'test_*.py'
node scripts/verify-cep.mjs
git diff --exit-code
```

`npm test` runs the original compiled TypeScript tests. Additional tests execute actual JSX in a fault-injecting host model, the generated private JSON host, a minimal UI DOM, transport failures and the C++ logger formatter. Python tests use synthetic Mach-O inputs/fake debugger frames. These tests cannot establish actual Adobe runtime compatibility. `check:host` remains a Node syntax check, not an ExtendScript engine check.

`build:cep` emits generated client/host bundles in cep and stages an explicit allowlisted installation payload in **dist/cep**. The staging directory is the only generated directory it replaces. The payload includes notices, exact SHA-256 file manifest and matching UI/host Build ID. verify-cep rejects dirty builds, wrong commit, missing/stale files, symlinks or invalid hashes. It is a consistency/integrity verifier, not a digital signature or protection against an attacker rewriting the entire package and manifest.

CI stores this internal artifact under its exact commit. Do not install the source cep directory instead of the verified staging payload. No automated installer is currently adapted to this canonical layout. No installed extension, AE process, user cache, preferences or security setting is changed by these commands.

## Synchronization / recovery limits

The two-second opt-in Experimental polling checkbox is an old read-only prototype, disabled by default, suspended while hidden and stopped after errors. It does not satisfy SYNC-001 and is not accepted as the final solution.

Initial empty host read recovery is bounded to three completed empty responses with 500/1000 ms delays. Commands, host error envelopes and timeouts are never retried. Startup no-composition discovery is bounded to 15 attempts, two seconds apart. Focus/visibility/Refresh can explicitly request another read. These policies are startup/recovery experiments, not evidence of an AE notification source. Re-evaluate/remove empty-read retries after controlled native cold-start tests prove their cause is fixed; global JSON isolation alone does not prove that historic cause.

After a command timeout, empty/malformed reply, operation identity mismatch or incomplete restoration, further writes are blocked in the current bridge/host instance. A successful read does not clear uncertainty. Inspect the project in native AE and recover the host/bridge deliberately; reload alone must not be represented as proof that the previous command failed. Last-known read data remains visibly STALE after refresh failure.

## Required native acceptance

AE 25.6.0.101 / CEP 12 / macOS Apple Silicon: exact installed Build ID/hash, clean load, native snapshot equality, frame timing, keyframes/stretch/remapping, project context identity, true Undo/Redo, rollback/error handling, reopen/restart and responsiveness. Other AE versions, Windows/Intel, arbitrary subframe values, distributable signing and complete event-based synchronization are not currently accepted.

The new research scripts are separate from this package. See ../research/ae-notifications/README.md. Debugger permissions and a disposable project do not imply permission to attach to an existing user work session or change system security.
