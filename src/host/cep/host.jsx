/* global app, CompItem, TextLayer, ShapeLayer, CameraLayer, LightLayer */

var FSTR_HOST_PROTOCOL_VERSION = 1;
var FSTR_CORE_CONTRACT_VERSION = 1;

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
    if (typeof value !== "number" || !isFinite(value) || Math.floor(value) !== value) {
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
        throw {
            code: "SUBFRAME_TIMING",
            message: fieldName + " is not aligned to a composition frame"
        };
    }
    fstrLineHostAssertInteger(frame, fieldName);
    return frame;
}

function fstrLineHostLayerType(layer) {
    if (layer.nullLayer) {
        return "null";
    }
    if (typeof TextLayer !== "undefined" && layer instanceof TextLayer) {
        return "text";
    }
    if (typeof ShapeLayer !== "undefined" && layer instanceof ShapeLayer) {
        return "shape";
    }
    if (typeof CameraLayer !== "undefined" && layer instanceof CameraLayer) {
        return "camera";
    }
    if (typeof LightLayer !== "undefined" && layer instanceof LightLayer) {
        return "light";
    }
    if (layer.hasAudio && !layer.hasVideo) {
        return "audio";
    }
    return "unknown";
}

function fstrLineHostLayerSnapshot(layer, comp) {
    if (typeof layer.id !== "number") {
        throw {
            code: "UNSUPPORTED_AE",
            message: "Layer.id is unavailable; After Effects 22.0+ is required"
        };
    }

    var inFrame = fstrLineHostToFrame(layer.inPoint, comp.frameDuration, "layer.inPoint");
    var outFrame = fstrLineHostToFrame(layer.outPoint, comp.frameDuration, "layer.outPoint");
    if (inFrame >= outFrame) {
        throw { code: "INVALID_RANGE", message: "Layer " + layer.id + " has an empty time range" };
    }

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
    var value = String(comp.id) + "|" + String(comp.frameDuration) + "|" + String(comp.duration);
    var index;
    for (index = 1; index <= comp.numLayers; index += 1) {
        var layer = comp.layer(index);
        value += "|" + String(layer.id) + ":" + String(layer.index);
        value += ":" + String(layer.startTime) + ":" + String(layer.inPoint) + ":" + String(layer.outPoint);
        value += ":" + String(!!layer.enabled) + ":" + String(!!layer.solo);
        value += ":" + String(!!layer.locked) + ":" + String(!!layer.audioEnabled);
    }

    var hash = 2166136261;
    for (index = 0; index < value.length; index += 1) {
        hash ^= value.charCodeAt(index);
        hash = (hash * 16777619) >>> 0;
    }
    return "fnv1a-" + String(hash >>> 0);
}

function fstrLineHostSnapshot(comp) {
    var layers = [];
    var index;
    for (index = 1; index <= comp.numLayers; index += 1) {
        layers.push(fstrLineHostLayerSnapshot(comp.layer(index), comp));
    }

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
    var index;
    for (index = 1; index <= comp.numLayers; index += 1) {
        var layer = comp.layer(index);
        if (layer.id === layerId) {
            return layer;
        }
    }
    throw { code: "LAYER_NOT_FOUND", message: "Layer " + layerId + " was not found" };
}

function fstrLineHostTargets(comp, layerIds) {
    if (!layerIds || !layerIds.length) {
        throw { code: "EMPTY_SELECTION", message: "At least one layer is required" };
    }
    var targets = [];
    var seen = {};
    var index;
    for (index = 0; index < layerIds.length; index += 1) {
        var layerId = Number(layerIds[index]);
        if (seen[layerId]) {
            continue;
        }
        seen[layerId] = true;
        targets.push(fstrLineHostFindLayer(comp, layerId));
    }
    return targets;
}

function fstrLineHostRequireUnlocked(layer, allowUnlock) {
    if (layer.locked && !allowUnlock) {
        throw { code: "LOCKED_LAYER", message: "Layer " + layer.id + " is locked" };
    }
}

function fstrLineHostPreflight(comp, command) {
    if (!command || command.commandVersion !== FSTR_CORE_CONTRACT_VERSION) {
        throw { code: "INVALID_COMMAND", message: "Unsupported or missing command version" };
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
        for (var moveIndex = 0; moveIndex < targets.length; moveIndex += 1) {
            fstrLineHostRequireUnlocked(targets[moveIndex]);
        }
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
        fstrLineHostRequireUnlocked(targets[0], command.layerSwitch === "locked" && command.value === false);
    } else if (command.type === "selectLayers") {
        targets = fstrLineHostTargets(comp, command.layerIds);
    } else {
        throw { code: "INVALID_COMMAND", message: "Unsupported command type" };
    }

    return { snapshot: snapshot, targets: targets };
}

function fstrLineHostCaptureState(comp) {
    var state = [];
    for (var index = 1; index <= comp.numLayers; index += 1) {
        var layer = comp.layer(index);
        state.push({
            layer: layer,
            startTime: layer.startTime,
            inPoint: layer.inPoint,
            outPoint: layer.outPoint,
            enabled: layer.enabled,
            solo: layer.solo,
            locked: layer.locked,
            audioEnabled: layer.audioEnabled,
            selected: layer.selected
        });
    }
    return state;
}

function fstrLineHostRestoreState(state) {
    for (var index = 0; index < state.length; index += 1) {
        var item = state[index];
        item.layer.startTime = item.startTime;
        item.layer.inPoint = item.inPoint;
        item.layer.outPoint = item.outPoint;
        item.layer.enabled = item.enabled;
        item.layer.solo = item.solo;
        item.layer.locked = item.locked;
        item.layer.audioEnabled = item.audioEnabled;
        item.layer.selected = item.selected;
    }
}

function fstrLineHostApply(comp, command, targets) {
    var frameDuration = comp.frameDuration;
    var index;
    if (command.type === "moveLayers") {
        var delta = command.deltaFrames * frameDuration;
        for (index = 0; index < targets.length; index += 1) {
            targets[index].startTime += delta;
            targets[index].inPoint += delta;
            targets[index].outPoint += delta;
        }
    } else if (command.type === "trimLayerIn") {
        targets[0].inPoint = command.newInFrame * frameDuration;
    } else if (command.type === "trimLayerOut") {
        targets[0].outPoint = command.newOutFrame * frameDuration;
    } else if (command.type === "setLayerSwitch") {
        targets[0][command.layerSwitch] = !!command.value;
    } else if (command.type === "selectLayers") {
        for (index = 1; index <= comp.numLayers; index += 1) {
            comp.layer(index).selected = false;
        }
        for (index = 0; index < targets.length; index += 1) {
            targets[index].selected = true;
        }
    }
}

var fstrLineHost = {
    diagnostics: function () {
        return fstrLineHostReply(function () {
            if (typeof FSTR_BUILD === "undefined") {
                throw { code: "MISSING_BUILD", message: "Host build metadata missing; rebuild CEP package" };
            }
            return fstrLineHostSuccess({ build: FSTR_BUILD, aeVersion: String(app.version) });
        });
    },
    readSnapshot: function () {
        return fstrLineHostReply(function () {
            return fstrLineHostSuccess(fstrLineHostSnapshot(fstrLineHostRequireComp()));
        });
    },
    executeCommand: function (command) {
        return fstrLineHostReply(function () {
            var comp = fstrLineHostRequireComp();
            var preflight = fstrLineHostPreflight(comp, command);
            var state = fstrLineHostCaptureState(comp);
            var groupOpened = false;
            try {
                app.beginUndoGroup("FSTR Line: " + command.type);
                groupOpened = true;
                fstrLineHostApply(comp, command, preflight.targets);
                return fstrLineHostSuccess({
                    operationId: command.operationId,
                    changed: true,
                    snapshot: fstrLineHostSnapshot(comp)
                });
            } catch (error) {
                try {
                    fstrLineHostRestoreState(state);
                } catch (restoreError) {
                    error.message = String(error.message || error) + "; rollback failed: " + String(restoreError.message || restoreError);
                }
                throw error;
            } finally {
                if (groupOpened) {
                    app.endUndoGroup();
                }
            }
        });
    }
};
