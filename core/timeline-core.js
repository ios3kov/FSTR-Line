(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.FSTRLineCore = api;
  }
}(this, function () {
  "use strict";

  function finiteNumber(value, name) {
    if (typeof value !== "number" || !isFinite(value)) {
      throw new TypeError(name + " must be a finite number");
    }
    return value;
  }

  function positiveNumber(value, name) {
    finiteNumber(value, name);
    if (value <= 0) {
      throw new RangeError(name + " must be > 0");
    }
    return value;
  }

  function overlaps(a, b) {
    return a.inFrame < b.outFrame && b.inFrame < a.outFrame;
  }

  function secondsToFrame(seconds, displayStartTime, frameDuration) {
    finiteNumber(seconds, "seconds");
    finiteNumber(displayStartTime, "displayStartTime");
    positiveNumber(frameDuration, "frameDuration");
    return Math.round((seconds - displayStartTime) / frameDuration);
  }

  function frameToSeconds(frame, displayStartTime, frameDuration) {
    finiteNumber(frame, "frame");
    finiteNumber(displayStartTime, "displayStartTime");
    positiveNumber(frameDuration, "frameDuration");
    return displayStartTime + (frame * frameDuration);
  }

  function normalizeSnapshot(snapshot) {
    if (!snapshot || !snapshot.comp || !snapshot.layers) {
      throw new TypeError("snapshot must contain comp and layers");
    }

    var comp = snapshot.comp;
    var frameDuration = positiveNumber(comp.frameDuration, "comp.frameDuration");
    var displayStartTime = finiteNumber(comp.displayStartTime || 0, "comp.displayStartTime");
    var layers = [];
    var i;
    var source;

    for (i = 0; i < snapshot.layers.length; i += 1) {
      source = snapshot.layers[i];
      layers.push({
        id: source.id,
        index: source.index,
        name: source.name,
        label: source.label,
        selected: !!source.selected,
        enabled: !!source.enabled,
        solo: !!source.solo,
        locked: !!source.locked,
        audioEnabled: !!source.audioEnabled,
        type: source.type,
        inPoint: source.inPoint,
        outPoint: source.outPoint,
        startTime: source.startTime,
        inFrame: secondsToFrame(source.inPoint, displayStartTime, frameDuration),
        outFrame: secondsToFrame(source.outPoint, displayStartTime, frameDuration),
        startFrame: secondsToFrame(source.startTime, displayStartTime, frameDuration)
      });
    }

    return {
      comp: comp,
      layers: layers
    };
  }

  function compareLayerOrder(a, b) {
    return a.index - b.index;
  }

  function packLayers(inputLayers) {
    if (!inputLayers || typeof inputLayers.slice !== "function") {
      throw new TypeError("layers must be an array");
    }

    var layers = inputLayers.slice().sort(compareLayerOrder);
    var placements = [];
    var tracks = [];
    var i;
    var j;
    var layer;
    var previous;
    var track;

    for (i = 0; i < layers.length; i += 1) {
      layer = layers[i];
      if (!(layer.outFrame > layer.inFrame)) {
        throw new RangeError("layer " + layer.id + " has invalid frame range");
      }

      track = 0;

      for (j = 0; j < placements.length; j += 1) {
        previous = placements[j];
        if (overlaps(previous.layer, layer) && track <= previous.track) {
          track = previous.track + 1;
        }
      }

      if (!tracks[track]) {
        tracks[track] = [];
      }

      tracks[track].push(layer);
      placements.push({
        id: layer.id,
        index: layer.index,
        track: track,
        layer: layer
      });
    }

    return {
      tracks: tracks,
      placements: placements,
      trackCount: tracks.length
    };
  }

  function validatePacking(result) {
    if (!result || !result.placements) {
      return { ok: false, error: "missing placements" };
    }

    var placements = result.placements;
    var i;
    var j;
    var a;
    var b;

    for (i = 0; i < placements.length; i += 1) {
      a = placements[i];
      for (j = i + 1; j < placements.length; j += 1) {
        b = placements[j];

        if (!overlaps(a.layer, b.layer)) {
          continue;
        }

        if (a.track === b.track) {
          return { ok: false, error: "overlapping layers share a track" };
        }

        if (a.index < b.index && !(a.track < b.track)) {
          return { ok: false, error: "AE Z-order was inverted" };
        }

        if (a.index > b.index && !(a.track > b.track)) {
          return { ok: false, error: "AE Z-order was inverted" };
        }
      }
    }

    return { ok: true };
  }

  return {
    overlaps: overlaps,
    secondsToFrame: secondsToFrame,
    frameToSeconds: frameToSeconds,
    normalizeSnapshot: normalizeSnapshot,
    packLayers: packLayers,
    validatePacking: validatePacking
  };
}));