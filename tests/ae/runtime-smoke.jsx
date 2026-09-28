#include "../../vendor/json2.js"

(function () {
    var report = {
        schemaVersion: 1,
        name: "FSTR Line AE Runtime Smoke",
        pass: false,
        aeVersion: app.version,
        startedAt: (new Date()).toUTCString(),
        checks: [],
        warnings: [],
        error: null,
        tempProject: null
    };

    function addCheck(name, pass, detail) {
        report.checks.push({
            name: name,
            pass: !!pass,
            detail: detail || null
        });

        if (!pass) {
            throw new Error(name + (detail ? ": " + detail : ""));
        }
    }

    function near(a, b, tolerance) {
        return Math.abs(a - b) <= tolerance;
    }

    function parseHost(raw) {
        var parsed = JSON.parse(raw);
        if (!parsed.ok) {
            throw new Error(
                parsed.error && parsed.error.message
                    ? parsed.error.message
                    : "Host operation failed."
            );
        }
        return parsed.data;
    }

    function findItemByName(name) {
        var i;
        for (i = 1; i <= app.project.numItems; i += 1) {
            if (app.project.item(i).name === name) {
                return app.project.item(i);
            }
        }
        return null;
    }

    function findLayerByName(comp, name) {
        var i;
        for (i = 1; i <= comp.numLayers; i += 1) {
            if (comp.layer(i).name === name) {
                return comp.layer(i);
            }
        }
        return null;
    }

    function securityAllowsFileWrites() {
        try {
            return app.preferences.getPrefAsLong(
                "Main Pref Section",
                "Pref_SCRIPTING_FILE_NETWORK_SECURITY"
            ) === 1;
        } catch (ignoreSecurityPref) {
            return false;
        }
    }

    function closeWithoutSaving() {
        try {
            if (app.project) {
                app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);
            }
        } catch (ignoreClose) {}
    }

    function cleanupTempFile(file) {
        if (!file || !file.exists) {
            return;
        }

        if (!securityAllowsFileWrites()) {
            report.warnings.push(
                "Temporary .aep remains because script file access is disabled: " + file.fsName
            );
            return;
        }

        try {
            if (!file.remove()) {
                report.warnings.push("Could not remove temporary .aep: " + file.fsName);
            }
        } catch (removeError) {
            report.warnings.push(
                "Could not remove temporary .aep: " +
                (removeError.message || String(removeError))
            );
        }
    }

    var tempFile = null;

    try {
        addCheck(
            "After Effects 22+",
            parseFloat(app.version) >= 22,
            "Detected " + app.version
        );

        addCheck(
            "Clean unsaved project",
            !!app.project && app.project.numItems === 0 && app.project.file === null,
            "Runtime smoke refuses to touch an existing user project."
        );

        var root = (new File($.fileName)).parent.parent.parent;
        var hostFile = new File(root.fsName + "/host/cep/host.jsx");

        addCheck("Host bridge file exists", hostFile.exists, hostFile.fsName);

        $.evalFile(hostFile);
        addCheck(
            "Host bridge loaded",
            !!$._fstr && typeof $._fstr.getSnapshot === "function"
        );

        var compName = "__FSTR_LINE_RUNTIME_SMOKE__";
        var comp = app.project.items.addComp(compName, 640, 360, 1, 12, 25);
        var frame = comp.frameDuration;
        var tolerance = frame / 1000;

        var layerA = comp.layers.addSolid([1, 0, 0], "A", 64, 64, 1, 12);
        var layerB = comp.layers.addSolid([0, 1, 0], "B", 64, 64, 1, 12);
        var layerC = comp.layers.addSolid([0, 0, 1], "C", 64, 64, 1, 12);

        layerA.startTime = 0;
        layerA.inPoint = 0;
        layerA.outPoint = 2;

        layerB.startTime = 2;
        layerB.inPoint = 2;
        layerB.outPoint = 4;

        layerC.startTime = 1;
        layerC.inPoint = 1;
        layerC.outPoint = 3;

        var viewer = comp.openInViewer();
        addCheck("Composition viewer opened", viewer !== null);
        addCheck(
            "Smoke comp is active",
            app.project.activeItem && app.project.activeItem.id === comp.id
        );

        var initial = parseHost($._fstr.getSnapshot());
        addCheck("Snapshot layer count", initial.layers.length === 3);

        var ids = {};
        var i;
        for (i = 0; i < initial.layers.length; i += 1) {
            ids[initial.layers[i].name] = initial.layers[i].id;
        }

        addCheck(
            "Persistent IDs are present and unique",
            ids.A > 0 && ids.B > 0 && ids.C > 0 &&
            ids.A !== ids.B && ids.A !== ids.C && ids.B !== ids.C
        );

        var selected = parseHost($._fstr.selectLayer(ids.B, false));
        var selectedCount = 0;
        var selectedId = null;
        for (i = 0; i < selected.layers.length; i += 1) {
            if (selected.layers[i].selected) {
                selectedCount += 1;
                selectedId = selected.layers[i].id;
            }
        }

        addCheck(
            "Selection bridge",
            selectedCount === 1 && selectedId === ids.B
        );

        layerB = findLayerByName(comp, "B");
        var beforeMove = {
            startTime: layerB.startTime,
            inPoint: layerB.inPoint,
            outPoint: layerB.outPoint
        };

        parseHost($._fstr.moveLayerFrames(ids.B, 2));
        addCheck(
            "Move startTime +2f",
            near(layerB.startTime, beforeMove.startTime + 2 * frame, tolerance)
        );
        addCheck(
            "Move preserves source trim",
            near(layerB.inPoint, beforeMove.inPoint + 2 * frame, tolerance) &&
            near(layerB.outPoint, beforeMove.outPoint + 2 * frame, tolerance)
        );

        var beforeTrimIn = {
            startTime: layerB.startTime,
            inPoint: layerB.inPoint,
            outPoint: layerB.outPoint
        };

        parseHost($._fstr.trimLayerInFrames(ids.B, 1));
        addCheck(
            "Trim In changes only inPoint",
            near(layerB.startTime, beforeTrimIn.startTime, tolerance) &&
            near(layerB.inPoint, beforeTrimIn.inPoint + frame, tolerance) &&
            near(layerB.outPoint, beforeTrimIn.outPoint, tolerance)
        );

        var beforeTrimOut = {
            startTime: layerB.startTime,
            inPoint: layerB.inPoint,
            outPoint: layerB.outPoint
        };

        parseHost($._fstr.trimLayerOutFrames(ids.B, -1));
        addCheck(
            "Trim Out changes only outPoint",
            near(layerB.startTime, beforeTrimOut.startTime, tolerance) &&
            near(layerB.inPoint, beforeTrimOut.inPoint, tolerance) &&
            near(layerB.outPoint, beforeTrimOut.outPoint - frame, tolerance)
        );

        var invalidBefore = {
            inPoint: layerB.inPoint,
            outPoint: layerB.outPoint
        };
        var invalid = JSON.parse($._fstr.trimLayerInFrames(ids.B, 100000));

        addCheck("Invalid trim is rejected", invalid.ok === false);
        addCheck(
            "Rejected trim is non-mutating",
            near(layerB.inPoint, invalidBefore.inPoint, tolerance) &&
            near(layerB.outPoint, invalidBefore.outPoint, tolerance)
        );

        tempFile = new File(Folder.temp.fsName + "/fstr-line-runtime-smoke.aep");
        report.tempProject = tempFile.fsName;

        app.project.save(tempFile);
        addCheck("Temporary project saved", tempFile.exists, tempFile.fsName);

        var savedIds = {
            A: ids.A,
            B: ids.B,
            C: ids.C
        };

        app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);
        app.open(tempFile);

        var reopenedComp = findItemByName(compName);
        addCheck(
            "Temporary project reopened",
            reopenedComp && reopenedComp instanceof CompItem
        );

        reopenedComp.openInViewer();

        var reopenedA = findLayerByName(reopenedComp, "A");
        var reopenedB = findLayerByName(reopenedComp, "B");
        var reopenedC = findLayerByName(reopenedComp, "C");

        addCheck(
            "Layer.id survives save/reopen",
            reopenedA && reopenedB && reopenedC &&
            reopenedA.id === savedIds.A &&
            reopenedB.id === savedIds.B &&
            reopenedC.id === savedIds.C
        );

        var reopenedSnapshot = parseHost($._fstr.getSnapshot());
        addCheck(
            "Bridge works after reopen",
            reopenedSnapshot.layers.length === 3 &&
            reopenedSnapshot.comp.id === reopenedComp.id
        );

        report.pass = true;
    } catch (error) {
        report.error = {
            message: error && error.message ? error.message : String(error),
            line: error && error.line ? error.line : null,
            fileName: error && error.fileName ? error.fileName : null
        };
    } finally {
        closeWithoutSaving();
        cleanupTempFile(tempFile);
        report.finishedAt = (new Date()).toUTCString();
        $._fstrRuntimeResult = JSON.stringify(report);
        $.writeln("FSTR_LINE_RUNTIME_RESULT=" + $._fstrRuntimeResult);
    }

    $._fstrRuntimeResult;
}());
