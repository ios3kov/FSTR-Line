# Testing and Clean Validation

## Rule

Every FSTR Line After Effects run must start from an identifiable clean extension build.

The user is not used as a debugging subsystem. Automated checks run first.

## Automated gate

Run:

    npm run check
    npm test
    npm run package:dev
    npm run verify:package

CI runs the same sequence and publishes the clean CEP extension directory as an artifact.

## Clean development install

Run:

    npm run install:dev

The installer:

1. refuses to install while After Effects is running;
2. rebuilds dist/FSTR-Line from an explicit source allowlist;
3. verifies the freshly built package before changing the installed extension;\n4. deletes every stale per-user extension carrying the FSTR Line bundle ID;
4. detects a system-level FSTR Line duplicate that would override the per-user copy;
5. removes only FSTR Line CEP cookie/cache records and FSTR Line CEP logs;
6. copies the newly packaged build;
7. enables unsigned CEP development for CSXS 11 and 12.

It never deletes another extension or the global After Effects media/cache database.

Adobe CEP user extension locations:

- macOS: ~/Library/Application Support/Adobe/CEP/extensions
- Windows: %APPDATA%/Adobe/CEP/extensions

## Reproducibility

The package includes BUILD_MANIFEST.json.

It contains a sorted SHA-256 + byte-size record for every packaged source file and has no timestamp. Rebuilding unchanged sources therefore produces the same manifest.

## Manual AE gate

Only after all automated checks are green:

1. start AE with the clean installed build;
2. open FSTR Line;
3. confirm panel docks;
4. compare snapshot/timing against the native timeline;
5. verify selection;
6. verify ±1 frame Move;
7. verify ±1 frame Trim In/Out;
8. undo each edit exactly once;
9. save/reopen and confirm stable layer identity;
10. collect CEP/renderer logs if any operation fails.

Performance claims require real profiling inside After Effects.

## CEP compatibility

FSTR Line requires AE 22+ because it uses persistent Layer.id.

The minimum runtime is CSXS 11. Adobe's integration matrix shows After Effects 18.4 on CEP 11 and After Effects 25 on CEP 12, which allows an AE 22+ floor without requiring CEP 12.


## Automated real-After-Effects smoke — macOS / Windows

Adobe documents sending JSX to After Effects, and the macOS runner uses JXA to execute the smoke file and then read its structured global result.

Run:

    npm run smoke:ae

Safety behavior:

- refuses to run if any After Effects process is already running;
- runtime JSX refuses any project that is not empty and unsaved;
- creates only temporary test items;
- tests the production host bridge;
- saves/reopens one temporary .aep to verify Layer.id persistence;
- closes the test project with DO_NOT_SAVE_CHANGES;
- runner quits the AE instance it launched;
- runner removes the temporary .aep when possible.

The runner chooses the newest After Effects application under /Applications. Override with:

    FSTR_AE_APP="/Applications/.../Adobe After Effects 2026.app" npm run smoke:ae

On Windows the runner discovers `AfterFX.exe`, launches it with Adobe's documented `-r` script mode, and the smoke sets `app.exitAfterLaunchAndEval` plus `app.exitCode` so the process can terminate with a machine-readable pass/fail code.

The smoke also records `app.memoryInUse` before and after the 10–1000 layer scale run.

For a one-command clean package/install + runtime smoke:

    npm run validate:ae


### macOS launcher robustness

The runner uses JXA because it is the practical automation bridge on macOS.

It retries AE startup/automation connection failures and first attempts `DoScriptFile`. If that fails, it falls back to `DoScript` with `$.evalFile(...)`. This avoids depending on one macOS automation path only.

macOS may still show the operating-system Automation permission prompt the first time Terminal controls After Effects. That permission is owned by macOS and is not bypassed by FSTR Line.


### Security-setting boundary

The installer does not enable Adobe `PlayerDebugMode`.

If unsigned CEP development is disabled, installation stops with `BLOCKED`. Enabling that setting requires explicit permission, or the project must use a signed CEP package.

The installer never terminates an already-running After Effects process.


## Runtime artifact identity

The real-AE smoke does not load the host bridge from the repository.

Before launching After Effects, the runner:

1. locates the installed per-user `FSTR-Line` CEP bundle;
2. reads `BUILD_MANIFEST.json` and generated Build Identity;
3. recalculates SHA-256 for every installed production file;
4. creates a unique Test Run ID and isolated temporary workspace;
5. launches AE with a generated wrapper carrying the expected Build ID and commit.

Inside After Effects, the smoke loads `host/cep/host.jsx` from the installed extension root and requires `getBuildInfo()` to match the expected Build ID and Git commit.

A missing result, stale Test Run ID, Build ID mismatch, Git commit mismatch or installed-file hash mismatch is FAIL, never PASS.

The test workspace and temporary project belong to the Test Run and are deleted by the external runner after AE exits.


## Test records

Each real-AE runner invocation writes a new record to:

    artifacts/ae-runtime/<Test Run ID>/test-record.json

The record contains:

- PASS / FAIL / BLOCKED status;
- Test Run ID;
- Build ID and Git commit when the installed payload could be verified;
- installed BUILD_MANIFEST SHA-256;
- runner and AE environment;
- initial-state facts;
- expected vs actual runtime identity;
- checks, timings, stress-scale measurements and memory data returned by AE;
- failure reason and explicit limitations.

A pre-existing/running After Effects instance produces BLOCKED, not PASS. Every invocation receives a new Test Run ID, so a previous PASS file cannot satisfy a later run.
