(function (root) {
  "use strict";

  var state = {
    snapshot: null,
    busy: false,
    buildIdentityMismatch: false,
    browserBuildInfo: null,
    hostBuildInfo: null
  };

  var nodes = {};

  function setBusy(value) {
    state.busy = value;
    document.body.classList.toggle("is-busy", value);

    var buttons = document.querySelectorAll("button");
    var i;
    for (i = 0; i < buttons.length; i += 1) {
      buttons[i].disabled = value;
    }
  }

  function setStatus(message, isError) {
    nodes.status.textContent = message || "";
    nodes.status.classList.toggle("is-error", !!isError);
  }

  function buildInfoText(info) {
    if (!info) {
      return "unavailable";
    }

    return [
      "Build ID: " + info.buildId,
      "Version: " + info.version,
      "Commit: " + info.gitCommit,
      "Git state: " + info.gitState,
      "Artifact: " + info.artifactType
    ].join("\n");
  }

  function renderDiagnostics() {
    var lines = [
      "Browser",
      buildInfoText(state.browserBuildInfo),
      "",
      "After Effects host",
      buildInfoText(state.hostBuildInfo),
      "",
      "Identity match: " + (state.buildIdentityMismatch ? "NO" : "YES")
    ];

    nodes.diagnosticsText.textContent = lines.join("\n");
  }

  function loadBuildIdentity() {
    state.browserBuildInfo = root.FSTRLineBuildInfo || null;

    return root.FSTRLineCEPAdapter.getBuildInfo()
      .then(function (hostInfo) {
        state.hostBuildInfo = hostInfo;
        state.buildIdentityMismatch =
          !state.browserBuildInfo ||
          !state.hostBuildInfo ||
          state.browserBuildInfo.buildId !== state.hostBuildInfo.buildId ||
          state.browserBuildInfo.gitCommit !== state.hostBuildInfo.gitCommit;

        renderDiagnostics();

        if (state.browserBuildInfo) {
          console.log(
            "[FSTR Line] " +
            state.browserBuildInfo.buildId +
            " commit=" +
            state.browserBuildInfo.gitCommit +
            " state=" +
            state.browserBuildInfo.gitState
          );
        }

        if (state.buildIdentityMismatch) {
          console.error("[FSTR Line] Browser/host Build Identity mismatch.");
        }
      })
      .catch(function (error) {
        state.hostBuildInfo = null;
        state.buildIdentityMismatch = true;
        renderDiagnostics();
        console.error("[FSTR Line] Build Identity check failed:", error);
      });
  }

  function firstSelectedLayer(snapshot) {
    if (!snapshot) {
      return null;
    }

    var i;
    for (i = 0; i < snapshot.layers.length; i += 1) {
      if (snapshot.layers[i].selected) {
        return snapshot.layers[i];
      }
    }

    return null;
  }

  function frameRange(normalized) {
    var durationFrames = Math.max(
      1,
      Math.round(normalized.comp.duration / normalized.comp.frameDuration)
    );
    var minFrame = 0;
    var maxFrame = durationFrames;
    var i;

    for (i = 0; i < normalized.layers.length; i += 1) {
      minFrame = Math.min(minFrame, normalized.layers[i].inFrame);
      maxFrame = Math.max(maxFrame, normalized.layers[i].outFrame);
    }

    if (maxFrame <= minFrame) {
      maxFrame = minFrame + 1;
    }

    return {
      min: minFrame,
      max: maxFrame,
      span: maxFrame - minFrame
    };
  }

  function clipTitle(layer) {
    return layer.name + "  [" + layer.inFrame + "–" + layer.outFrame + "f]";
  }

  function renderEmpty() {
    nodes.compMeta.textContent = "No active composition";
    nodes.timeline.innerHTML = "";
    nodes.selection.textContent = "Select a clip";
    nodes.editor.hidden = true;
  }

  function renderTimeline(snapshot) {
    if (!snapshot) {
      renderEmpty();
      setStatus("Open a composition in After Effects.", false);
      return;
    }

    var normalized = root.FSTRLineCore.normalizeSnapshot(snapshot);
    var packed = root.FSTRLineCore.packLayers(normalized.layers);
    var validation = root.FSTRLineCore.validatePacking(packed);

    if (!validation.ok) {
      throw new Error("Packing invariant failed: " + validation.error);
    }

    var range = frameRange(normalized);
    var selected = firstSelectedLayer(snapshot);
    var fragment = document.createDocumentFragment();
    var trackIndex;
    var clipIndex;

    nodes.compMeta.textContent =
      snapshot.comp.name +
      " · " +
      snapshot.comp.frameRate.toFixed(3) +
      " fps · " +
      snapshot.layers.length +
      " layers · " +
      packed.trackCount +
      " tracks";

    nodes.timeline.innerHTML = "";

    for (trackIndex = 0; trackIndex < packed.tracks.length; trackIndex += 1) {
      var row = document.createElement("div");
      row.className = "track";

      var label = document.createElement("div");
      label.className = "track-label";
      label.textContent = "V" + (trackIndex + 1);
      row.appendChild(label);

      var lane = document.createElement("div");
      lane.className = "track-lane";

      for (clipIndex = 0; clipIndex < packed.tracks[trackIndex].length; clipIndex += 1) {
        var layer = packed.tracks[trackIndex][clipIndex];
        var clip = document.createElement("button");
        var left = ((layer.inFrame - range.min) / range.span) * 100;
        var width = ((layer.outFrame - layer.inFrame) / range.span) * 100;

        clip.type = "button";
        clip.className = "clip label-" + layer.label + (layer.selected ? " is-selected" : "");
        clip.style.left = left + "%";
        clip.style.width = Math.max(width, 0.35) + "%";
        clip.title = clipTitle(layer);
        clip.dataset.layerId = String(layer.id);
        clip.textContent = layer.name;

        lane.appendChild(clip);
      }

      row.appendChild(lane);
      fragment.appendChild(row);
    }

    nodes.timeline.appendChild(fragment);

    if (selected) {
      nodes.selection.textContent =
        selected.name +
        " · " +
        selected.inPoint.toFixed(3) +
        "s → " +
        selected.outPoint.toFixed(3) +
        "s";
      nodes.editor.hidden = false;
      nodes.editor.dataset.layerId = String(selected.id);
    } else {
      nodes.selection.textContent = "Select a clip";
      nodes.editor.hidden = true;
      delete nodes.editor.dataset.layerId;
    }

    if (state.buildIdentityMismatch) {
      setStatus("Build Identity mismatch — open Diagnostics.", true);
    } else {
      setStatus("Synced with After Effects.", false);
    }
  }

  function applySnapshot(snapshot) {
    state.snapshot = snapshot;
    renderTimeline(snapshot);
  }

  function run(operation) {
    if (state.busy) {
      return;
    }

    setBusy(true);
    setStatus("Updating After Effects…", false);

    var pending;
    try {
      pending = operation();
    } catch (error) {
      setStatus(error.message || String(error), true);
      setBusy(false);
      return;
    }

    Promise.resolve(pending)
      .then(function (snapshot) {
        applySnapshot(snapshot);
      })
      .catch(function (error) {
        setStatus(error.message || String(error), true);
      })
      .then(function () {
        setBusy(false);
      });
  }

  function refresh() {
    run(function () {
      return root.FSTRLineCEPAdapter.getSnapshot();
    });
  }

  function onTimelineClick(event) {
    var clip = event.target.closest(".clip");
    if (!clip || state.busy) {
      return;
    }

    var layerId = Number(clip.dataset.layerId);
    run(function () {
      return root.FSTRLineCEPAdapter.selectLayer(layerId, event.shiftKey);
    });
  }

  function onEditClick(event) {
    var button = event.target.closest("button[data-command]");
    if (!button || state.busy) {
      return;
    }

    var layerId = Number(nodes.editor.dataset.layerId);
    var command = button.dataset.command;

    run(function () {
      if (command === "move-back") {
        return root.FSTRLineCEPAdapter.moveLayerFrames(layerId, -1);
      }
      if (command === "move-forward") {
        return root.FSTRLineCEPAdapter.moveLayerFrames(layerId, 1);
      }
      if (command === "trim-in-back") {
        return root.FSTRLineCEPAdapter.trimLayerInFrames(layerId, -1);
      }
      if (command === "trim-in-forward") {
        return root.FSTRLineCEPAdapter.trimLayerInFrames(layerId, 1);
      }
      if (command === "trim-out-back") {
        return root.FSTRLineCEPAdapter.trimLayerOutFrames(layerId, -1);
      }
      if (command === "trim-out-forward") {
        return root.FSTRLineCEPAdapter.trimLayerOutFrames(layerId, 1);
      }

      return Promise.reject(new Error("Unknown edit command."));
    });
  }

  function init() {
    nodes.status = document.getElementById("status");
    nodes.compMeta = document.getElementById("comp-meta");
    nodes.timeline = document.getElementById("timeline");
    nodes.selection = document.getElementById("selection");
    nodes.editor = document.getElementById("editor");
    nodes.diagnostics = document.getElementById("diagnostics");
    nodes.diagnosticsText = document.getElementById("diagnostics-text");

    document.getElementById("diagnostics-toggle").addEventListener("click", function () {
      nodes.diagnostics.hidden = !nodes.diagnostics.hidden;
    });
    document.getElementById("refresh").addEventListener("click", refresh);
    nodes.timeline.addEventListener("click", onTimelineClick);
    nodes.editor.addEventListener("click", onEditClick);

    loadBuildIdentity().then(function () {
      refresh();
    });
  }

  document.addEventListener("DOMContentLoaded", init);
}(window));
