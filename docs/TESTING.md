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


## Automated real-After-Effects smoke — macOS

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

The runtime JSX is platform-independent. Automated launcher support for Windows remains a separate compatibility task.
