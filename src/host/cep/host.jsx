/* global app, CompItem, TextLayer, ShapeLayer, CameraLayer, LightLayer */

var FSTR_HOST_PROTOCOL_VERSION = 1;
var FSTR_CORE_CONTRACT_VERSION = 1;

// Opaque revision identity. References are checked in addition to persistent IDs.
// Actual AE wrapper lifetime semantics remain a required runtime gate.
var fstrLineHostSession = String(new Date().getTime()) + "-" + String(Math.random());
var fstrLineHostContext = { project: null, comp: null, signature: null, revision: 0 };
var fstrLineHostWriteFault = false;

function fstrLineHostError(code, message) {
    return {
        protocolVersion: FSTR_HOST_PROTOCOL_VERSION,
        ok: false,
        error: { code: String(code), message: String(message) }
    };
}

function fstrLineHostSuccess(data) {
    return {
        protocolVersion: FSTR_HOST_PROTOCOL_VERSION,
        ok: true,
        data: data
    };
}

function fstrLineHostReply(factory) {
    try {
        return JSON.stringify(factory());
    } catch (error) {
        return JSON.stringify(fstrLineHostError(
            error && error.code ? error.code : "HOST_EXCEPTION",
            error && error.message ? error.message : String(error)
        ));
    }
}

function fstrLineHostRequireComp() {
    if (!app.project || !app.project.activeItem || !(app.project.activeItem instanceof CompItem)) {
        throw { code: "NO_ACTIVE_COMP", message: "No active After Effects composition" };
    }
    if (typeof app.project.activeItem.id !== "number") {
        throw { code: "UNSUPPORTED_AE", message: "Composition.id is unavailable; After Effects 22.0+ is required" };
    }
    return app.project.activeItem;
}

function fstrLineHostAssertInteger(value, fieldName) {
    if (typeof value !== "number" || !isFinite(value) || Math.floor(value) !== value || Math.abs(value) > 9007199254740991) {
        throw { code: "INVALID_FRAME", message: fieldName + " must be an integer frame" };
    }
}

function fstrLineHostFrameRate(value) {
    var knownRates = [
        { value: 23.976023976, numerator: 24000, denominator: 1001 },
        { value: 29.97002997, numerator: 30000, denominator: 1001 },
        { value: 59.94005994, numerator: 60000, denominator: 1001 }
    ];
    var index;
    for (index = 0; index < knownRates.length; index += 1) {
        if (Math.abs(value - knownRates[index].value) < 0.0001) {
            return {
                numerator: knownRates[index].numerator,
                denominator: knownRates[index].denominator
            };
        }
    }
    var numerator = Math.round(value * 1000);
    var denominator = 1000;
    var divisor = fstrLineHostGcd(numerator, denominator);
    return { numerator: numerator / divisor, denominator: denominator / divisor };
}

function fstrLineHostGcd(first, second) {
    var left = Math.abs(first);
    var right = Math.abs(second);
    while (right !== 0) {
        var remainder = left % right;
        left = right;
        right = remainder;
    }
    return left || 1;
}

function fstrLineHostToFrame(seconds, frameDuration, fieldName) {
    var rawFrame = seconds / frameDuration;
    var frame = Math.round(rawFrame);
    if (Math.abs(rawFrame - frame) > 0.00001) {
        throw { code: "SUBFRAME_TIMING", message: fieldName + " is not aligned to a composition frame" };
    }
    fstrLineHostAssertInteger(frame, fieldName);
    return frame;
}

function fstrLineHostLayerType(layer) {
    if (layer.nullLayer) return "null";
    if (typeof TextLayer !== "undefined" && layer instanceof TextLayer) return "text";
    if (typeof ShapeLayer !== "undefined" && layer instanceof ShapeLayer) return "shape";
    if (typeof CameraLayer !== "undefined" && layer instanceof CameraLayer) return "camera";
    if (typeof LightLayer !== "undefined" && layer instanceof LightLayer) return "light";
    if (layer.hasAudio && !layer.hasVideo) return "audio";
    return "unknown";
}

function fstrLineHostLayerSnapshot(layer, comp) {
    if (typeof layer.id !== "number") {
        throw { code: "UNSUPPORTED_AE", message: "Layer.id is unavailable; After Effects 22.0+ is required" };
    }
    var inFrame = fstrLineHostToFrame(layer.inPoint, comp.frameDuration, "layer.inPoint");
    var outFrame = fstrLineHostToFrame(layer.outPoint, comp.frameDuration, "layer.outPoint");
    if (inFrame >= outFrame) throw { code: "INVALID_RANGE", message: "Layer " + layer.id + " has an empty time range" };
    return {
        layerId: layer.id,
        index: layer.index,
        name: layer.name,
        type: fstrLineHostLayerType(layer),
        startFrame: fstrLineHostToFrame(layer.startTime, comp.frameDuration, "layer.startTime"),
        inFrame: inFrame,
        outFrame: outFrame,
        label: layer.label,
        selected: !!layer.selected,
        enabled: !!layer.enabled,
        solo: !!layer.solo,
        locked: !!layer.locked,
        audioEnabled: !!layer.audioEnabled,
        capabilities: {
            canMove: !layer.locked,
            canTrimIn: !layer.locked,
            canTrimOut: !layer.locked,
            canSetSwitches: !layer.locked,
            canReorder: !layer.locked
        }
    };
}

function fstrLineHostRevision(comp) {
    // Exact serialization, not a collision-prone hash of partially covered fields.
    // This is a read-time guard, NOT an AE event source or background monitor.
    var state = [comp.id, comp.name, comp.frameDuration, comp.duration, comp.time];
    var index;
    for (index = 1; index <= comp.numLayers; index += 1) {
        var layer = comp.layer(index);
        state.push([layer.id, layer.index, layer.name, layer.label,
            layer.startTime, layer.inPoint, layer.outPoint,
            !!layer.enabled, !!layer.solo, !!layer.locked,
            !!layer.audioEnabled, !!layer.selected]);
    }
    var signature = JSON.stringify(state);
    if (fstrLineHostContext.project !== app.project || fstrLineHostContext.comp !== comp ||
            fstrLineHostContext.signature !== signature) {
        fstrLineHostContext.project = app.project;
        fstrLineHostContext.comp = comp;
        fstrLineHostContext.signature = signature;
        fstrLineHostContext.revision += 1;
    }
    return fstrLineHostSession + ":" + fstrLineHostContext.revision;
}

function fstrLineHostSnapshot(comp) {
    var layers = [];
    var index;
    for (index = 1; index <= comp.numLayers; index += 1) layers.push(fstrLineHostLayerSnapshot(comp.layer(index), comp));
    return {
        schemaVersion: FSTR_CORE_CONTRACT_VERSION,
        compositionId: String(comp.id),
        compositionName: comp.name,
        frameRate: fstrLineHostFrameRate(comp.frameRate),
        durationFrames: fstrLineHostToFrame(comp.duration, comp.frameDuration, "composition.duration"),
        currentFrame: fstrLineHostToFrame(comp.time, comp.frameDuration, "composition.time"),
        layers: layers,
        revision: fstrLineHostRevision(comp)
    };
}

function fstrLineHostFindLayer(comp, layerId) {
    for (var index = 1; index <= comp.numLayers; index += 1) {
        var layer = comp.layer(index);
        if (layer.id === layerId) return layer;
    }
    throw { code: "LAYER_NOT_FOUND", message: "Layer " + layerId + " was not found" };
}

function fstrLineHostTargets(comp, layerIds) {
    if (!layerIds || !layerIds.length) throw { code: "EMPTY_SELECTION", message: "At least one layer is required" };
    var targets = [];
    var seen = {};
    for (var index = 0; index < layerIds.length; index += 1) {
        var layerId = layerIds[index];
        fstrLineHostAssertInteger(layerId, "layerId");
        if (layerId <= 0) throw { code: "INVALID_COMMAND", message: "Invalid layerId" };
        if (seen[layerId]) continue;
        seen[layerId] = true;
        targets.push(fstrLineHostFindLayer(comp, layerId));
    }
    return targets;
}

function fstrLineHostRequireUnlocked(layer, allowUnlock) {
    if (layer.locked && !allowUnlock) throw { code: "LOCKED_LAYER", message: "Layer " + layer.id + " is locked" };
}

function fstrLineHostPreflight(comp, command) {
    if (!command || command.commandVersion !== FSTR_CORE_CONTRACT_VERSION) {
        throw { code: "INVALID_COMMAND", message: "Unsupported or missing command version" };
    }
    if (typeof command.operationId !== "string" || !command.operationId) {
        throw { code: "INVALID_COMMAND", message: "operationId must be a non-empty string" };
    }
    var snapshot = fstrLineHostSnapshot(comp);
    if (!command.guard || String(command.guard.compositionId) !== String(comp.id)) {
        throw { code: "WRONG_COMPOSITION", message: "Command targets another composition" };
    }
    if (command.guard.revision !== snapshot.revision) {
        throw { code: "STALE_SNAPSHOT", message: "Command was created from a stale snapshot" };
    }
    var targets;
    if (command.type === "moveLayers") {
        fstrLineHostAssertInteger(command.deltaFrames, "deltaFrames");
        targets = fstrLineHostTargets(comp, command.layerIds);
        for (var moveIndex = 0; moveIndex < targets.length; moveIndex += 1) fstrLineHostRequireUnlocked(targets[moveIndex]);
    } else if (command.type === "trimLayerIn") {
        fstrLineHostAssertInteger(command.newInFrame, "newInFrame");
        targets = [fstrLineHostFindLayer(comp, command.layerId)];
        fstrLineHostRequireUnlocked(targets[0]);
        if (command.newInFrame >= fstrLineHostToFrame(targets[0].outPoint, comp.frameDuration, "layer.outPoint")) {
            throw { code: "INVALID_TIMING", message: "Trim in must remain before out point" };
        }
    } else if (command.type === "trimLayerOut") {
        fstrLineHostAssertInteger(command.newOutFrame, "newOutFrame");
        targets = [fstrLineHostFindLayer(comp, command.layerId)];
        fstrLineHostRequireUnlocked(targets[0]);
        if (command.newOutFrame <= fstrLineHostToFrame(targets[0].inPoint, comp.frameDuration, "layer.inPoint")) {
            throw { code: "INVALID_TIMING", message: "Trim out must remain after in point" };
        }
    } else if (command.type === "setLayerSwitch") {
        targets = [fstrLineHostFindLayer(comp, command.layerId)];
        if (command.layerSwitch !== "enabled" && command.layerSwitch !== "solo" &&
                command.layerSwitch !== "locked" && command.layerSwitch !== "audioEnabled") {
            throw { code: "INVALID_COMMAND", message: "Unsupported layer switch" };
        }
        if (typeof command.value !== "boolean") throw { code: "INVALID_COMMAND", message: "Switch value must be boolean" };
        if (typeof targets[0][command.layerSwitch] !== "boolean") {
            throw { code: "UNSUPPORTED_OPERATION", message: "Switch unavailable on this layer type" };
        }
        fstrLineHostRequireUnlocked(targets[0], command.layerSwitch === "locked" && command.value === false);
    } else if (command.type === "selectLayers") {
        targets = fstrLineHostTargets(comp, command.layerIds);
    } else {
        throw { code: "INVALID_COMMAND", message: "Unsupported command type" };
    }
    return { snapshot: snapshot, targets: targets };
}

function fstrLineHostPlan(comp, command, targets) {
    var plan = [];
    var index;
    function add(layer, fields, values) {
        var before = [];
        var changed = false;
        for (var field = 0; field < fields.length; field += 1) {
            before.push(layer[fields[field]]);
            if (before[field] !== values[field]) changed = true;
            if (typeof values[field] === "number") {
                fstrLineHostAssertInteger(Math.round(values[field] / comp.frameDuration), fields[field]);
                if (!isFinite(values[field])) throw { code: "INVALID_TIMING", message: "Non-finite target time" };
            }
        }
        if (changed) plan.push({ layer: layer, layerId: layer.id, fields: fields, before: before, after: values, touched: false });
    }
    if (command.type === "moveLayers") {
        var delta = command.deltaFrames * comp.frameDuration;
        for (index = 0; index < targets.length; index += 1) {
            var layer = targets[index];
            // Read all originals before any setter. startTime may move in/out itself.
            add(layer, ["startTime", "inPoint", "outPoint"],
                [layer.startTime + delta, layer.inPoint + delta, layer.outPoint + delta]);
        }
    } else if (command.type === "trimLayerIn") {
        add(targets[0], ["inPoint"], [command.newInFrame * comp.frameDuration]);
    } else if (command.type === "trimLayerOut") {
        add(targets[0], ["outPoint"], [command.newOutFrame * comp.frameDuration]);
    } else if (command.type === "setLayerSwitch") {
        add(targets[0], [command.layerSwitch], [command.value]);
    } else if (command.type === "selectLayers") {
        for (index = 1; index <= comp.numLayers; index += 1) {
            var candidate = comp.layer(index);
            var selected = false;
            for (var targetIndex = 0; targetIndex < targets.length; targetIndex += 1) {
                if (targets[targetIndex].id === candidate.id) selected = true;
            }
            add(candidate, ["selected"], [selected]);
        }
    }
    return plan;
}

function fstrLineHostSameValue(actual, expected) {
    return typeof expected === "number"
        ? typeof actual === "number" && isFinite(actual) && Math.abs(actual - expected) <= 0.00000001
        : actual === expected;
}

function fstrLineHostApplyPlan(plan) {
    for (var index = 0; index < plan.length; index += 1) {
        var item = plan[index];
        item.touched = true;
        for (var field = 0; field < item.fields.length; field += 1) {
            if (!fstrLineHostSameValue(item.layer[item.fields[field]], item.after[field])) item.layer[item.fields[field]] = item.after[field];
        }
        for (var check = 0; check < item.fields.length; check += 1) {
            if (!fstrLineHostSameValue(item.layer[item.fields[check]], item.after[check])) {
                throw { code: "HOST_POSTCONDITION", message: "Host did not apply the requested value" };
            }
        }
    }
}

function fstrLineHostRestorePlan(plan) {
    var failures = [];
    // Continue restoring other targets even when one setter fails. Never touch
    // unrelated layers or unrelated properties (notably locked background layers).
    for (var index = plan.length - 1; index >= 0; index -= 1) {
        var item = plan[index];
        if (!item.touched) continue;
        for (var field = 0; field < item.fields.length; field += 1) {
            try {
                if (!fstrLineHostSameValue(item.layer[item.fields[field]], item.before[field])) item.layer[item.fields[field]] = item.before[field];
            } catch (error) {
                failures.push(String(item.layerId) + ":" + item.fields[field]);
            }
        }
        for (var check = 0; check < item.fields.length; check += 1) {
            try {
                if (!fstrLineHostSameValue(item.layer[item.fields[check]], item.before[check])) failures.push(String(item.layerId) + ":" + item.fields[check] + ":mismatch");
            } catch (readError) {
                failures.push(String(item.layerId) + ":" + item.fields[check] + ":unreadable");
            }
        }
    }
    return failures;
}

var fstrLineHost = {
    diagnostics: function () {
        return fstrLineHostReply(function () {
            if (typeof FSTR_BUILD === "undefined") throw { code: "MISSING_BUILD", message: "Host build metadata missing; rebuild CEP package" };
            return fstrLineHostSuccess({ build: FSTR_BUILD, aeVersion: String(app.version), writesDisabled: fstrLineHostWriteFault });
        });
    },
    readSnapshot: function () {
        return fstrLineHostReply(function () { return fstrLineHostSuccess(fstrLineHostSnapshot(fstrLineHostRequireComp())); });
    },
    executeCommand: function (command) {
        return fstrLineHostReply(function () {
            if (fstrLineHostWriteFault) {
                throw { code: "RECOVERY_REQUIRED", message: "Writes disabled after an uncertain host failure. Inspect the native project and restart the host before editing." };
            }
            var comp = fstrLineHostRequireComp();
            var preflight = fstrLineHostPreflight(comp, command);
            var plan = fstrLineHostPlan(comp, command, preflight.targets);
            if (plan.length === 0) return fstrLineHostSuccess({ operationId: command.operationId, changed: false, snapshot: preflight.snapshot });
            var groupOpened = false;
            try {
                app.beginUndoGroup("FSTR Line: " + command.type);
                groupOpened = true;
                fstrLineHostApplyPlan(plan);
                return fstrLineHostSuccess({ operationId: command.operationId, changed: true, snapshot: fstrLineHostSnapshot(comp) });
            } catch (error) {
                var failures = fstrLineHostRestorePlan(plan);
                if (failures.length > 0) {
                    fstrLineHostWriteFault = true;
                    throw { code: "ROLLBACK_FAILED", message: "Operation failed and restoration is incomplete; further writes disabled. Fields: " + failures.join(", ") };
                }
                throw error;
            } finally {
                if (groupOpened) {
                    try { app.endUndoGroup(); }
                    catch (undoError) {
                        fstrLineHostWriteFault = true;
                        throw { code: "RECOVERY_REQUIRED", message: "Unable to close the Undo group; operation outcome must be checked in native AE." };
                    }
                }
            }
        });
    }
};
