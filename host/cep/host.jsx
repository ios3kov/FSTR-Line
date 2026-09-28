#include "../../vendor/json2.js"

if (!$._fstr) {
    $._fstr = {};
}

(function (api) {
    function response(ok, data, error) {
        return JSON.stringify({
            ok: ok,
            data: data === undefined ? null : data,
            error: error || null
        });
    }

    function guard(fn) {
        try {
            return response(true, fn(), null);
        } catch (error) {
            return response(false, null, {
                message: error && error.message ? error.message : String(error),
                line: error && error.line ? error.line : null
            });
        }
    }

    function activeCompOrNull() {
        if (!app.project) {
            return null;
        }

        var item = app.project.activeItem;
        return item && item instanceof CompItem ? item : null;
    }

    function requireComp() {
        var comp = activeCompOrNull();
        if (!comp) {
            throw new Error("No active composition.");
        }
        return comp;
    }

    function requireInteger(value, name) {
        if (typeof value !== "number" || !isFinite(value) || Math.floor(value) !== value) {
            throw new Error(name + " must be an integer.");
        }
        return value;
    }

    function findLayer(comp, layerId) {
        requireInteger(layerId, "layerId");

        var i;
        for (i = 1; i <= comp.numLayers; i += 1) {
            if (comp.layer(i).id === layerId) {
                return comp.layer(i);
            }
        }

        throw new Error("Layer " + layerId + " was not found in the active composition.");
    }

    function layerType(layer) {
        if (layer instanceof CameraLayer) {
            return "camera";
        }
        if (layer instanceof LightLayer) {
            return "light";
        }
        if (layer instanceof TextLayer) {
            return "text";
        }
        if (layer instanceof ShapeLayer) {
            return "shape";
        }
        if (layer instanceof AVLayer) {
            try {
                if (layer.nullLayer) {
                    return "null";
                }
            } catch (ignoreNullLayer) {}

            try {
                if (layer.adjustmentLayer) {
                    return "adjustment";
                }
            } catch (ignoreAdjustmentLayer) {}

            try {
                if (layer.source && layer.source instanceof CompItem) {
                    return "precomp";
                }
            } catch (ignoreSourceType) {}

            return "av";
        }

        return "layer";
    }

    function sourceId(layer) {
        try {
            return layer.source && layer.source.id !== undefined ? layer.source.id : null;
        } catch (ignoreSource) {
            return null;
        }
    }

    function audioEnabled(layer) {
        try {
            return !!layer.audioEnabled;
        } catch (ignoreAudio) {
            return false;
        }
    }

    function snapshot(comp) {
        if (!comp) {
            return null;
        }

        var layers = [];
        var i;
        var layer;

        for (i = 1; i <= comp.numLayers; i += 1) {
            layer = comp.layer(i);
            layers.push({
                id: layer.id,
                index: layer.index,
                name: layer.name,
                inPoint: layer.inPoint,
                outPoint: layer.outPoint,
                startTime: layer.startTime,
                label: layer.label,
                selected: !!layer.selected,
                enabled: !!layer.enabled,
                solo: !!layer.solo,
                locked: !!layer.locked,
                audioEnabled: audioEnabled(layer),
                type: layerType(layer),
                sourceId: sourceId(layer)
            });
        }

        return {
            bridgeVersion: 1,
            comp: {
                id: comp.id,
                name: comp.name,
                duration: comp.duration,
                frameRate: comp.frameRate,
                frameDuration: comp.frameDuration,
                displayStartTime: comp.displayStartTime,
                displayStartFrame: comp.displayStartFrame,
                time: comp.time,
                numLayers: comp.numLayers
            },
            layers: layers
        };
    }

    function withUndo(label, fn) {
        app.beginUndoGroup(label);
        try {
            return fn();
        } finally {
            app.endUndoGroup();
        }
    }

    api.getBuildInfo = function () {
        return guard(function () {
            return $._fstrBuildInfo || null;
        });
    };

    api.getSnapshot = function () {
        return guard(function () {
            return snapshot(activeCompOrNull());
        });
    };

    api.selectLayer = function (layerId, additive) {
        return guard(function () {
            var comp = requireComp();
            var layer = findLayer(comp, layerId);
            var selected;
            var i;

            if (!additive) {
                selected = comp.selectedLayers;
                for (i = selected.length - 1; i >= 0; i -= 1) {
                    selected[i].selected = false;
                }
            }

            layer.selected = true;
            return snapshot(comp);
        });
    };

    api.moveLayerFrames = function (layerId, deltaFrames) {
        return guard(function () {
            var comp = requireComp();
            var layer = findLayer(comp, layerId);
            requireInteger(deltaFrames, "deltaFrames");

            if (deltaFrames !== 0) {
                withUndo("FSTR Line: Move Clip", function () {
                    layer.startTime = layer.startTime + (deltaFrames * comp.frameDuration);
                });
            }

            return snapshot(comp);
        });
    };

    api.trimLayerInFrames = function (layerId, deltaFrames) {
        return guard(function () {
            var comp = requireComp();
            var layer = findLayer(comp, layerId);
            requireInteger(deltaFrames, "deltaFrames");

            if (deltaFrames !== 0) {
                var nextInPoint = layer.inPoint + (deltaFrames * comp.frameDuration);
                if (!(nextInPoint < layer.outPoint)) {
                    throw new Error("Trim In would make the layer duration zero or negative.");
                }

                withUndo("FSTR Line: Trim In", function () {
                    layer.inPoint = nextInPoint;
                });
            }

            return snapshot(comp);
        });
    };

    api.trimLayerOutFrames = function (layerId, deltaFrames) {
        return guard(function () {
            var comp = requireComp();
            var layer = findLayer(comp, layerId);
            requireInteger(deltaFrames, "deltaFrames");

            if (deltaFrames !== 0) {
                var nextOutPoint = layer.outPoint + (deltaFrames * comp.frameDuration);
                if (!(nextOutPoint > layer.inPoint)) {
                    throw new Error("Trim Out would make the layer duration zero or negative.");
                }

                withUndo("FSTR Line: Trim Out", function () {
                    layer.outPoint = nextOutPoint;
                });
            }

            return snapshot(comp);
        });
    };
    try {
        if ($._fstrBuildInfo) {
            $.writeln("FSTR_LINE_BUILD=" + JSON.stringify($._fstrBuildInfo));
        }
    } catch (ignoreBuildLog) {}
}($._fstr));
