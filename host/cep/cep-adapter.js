(function (root) {
  "use strict";

  var csInterface = null;

  function getCSInterface() {
    if (!csInterface) {
      if (typeof root.CSInterface !== "function") {
        throw new Error("Adobe CEP CSInterface is not available.");
      }
      csInterface = new root.CSInterface();
    }
    return csInterface;
  }

  function integer(value, name) {
    if (typeof value !== "number" || !isFinite(value) || Math.floor(value) !== value) {
      throw new TypeError(name + " must be an integer");
    }
    return value;
  }

  function callHost(expression) {
    return new Promise(function (resolve, reject) {
      var bridge;

      try {
        bridge = getCSInterface();
      } catch (error) {
        reject(error);
        return;
      }

      bridge.evalScript(expression, function (raw) {
        if (!raw || raw === "EvalScript error.") {
          reject(new Error("After Effects host bridge returned an evalScript error."));
          return;
        }

        var payload;
        try {
          payload = JSON.parse(raw);
        } catch (error) {
          reject(new Error("Invalid response from After Effects host bridge."));
          return;
        }

        if (!payload.ok) {
          reject(new Error(
            payload.error && payload.error.message
              ? payload.error.message
              : "After Effects host operation failed."
          ));
          return;
        }

        resolve(payload.data);
      });
    });
  }

  function boolLiteral(value) {
    return value ? "true" : "false";
  }

  function layerCall(name, layerId, deltaFrames) {
    integer(layerId, "layerId");
    integer(deltaFrames, "deltaFrames");
    return callHost("$._fstr." + name + "(" + layerId + "," + deltaFrames + ")");
  }

  root.FSTRLineCEPAdapter = {
    getSnapshot: function () {
      return callHost("$._fstr.getSnapshot()");
    },

    selectLayer: function (layerId, additive) {
      integer(layerId, "layerId");
      return callHost("$._fstr.selectLayer(" + layerId + "," + boolLiteral(additive) + ")");
    },

    moveLayerFrames: function (layerId, deltaFrames) {
      return layerCall("moveLayerFrames", layerId, deltaFrames);
    },

    trimLayerInFrames: function (layerId, deltaFrames) {
      return layerCall("trimLayerInFrames", layerId, deltaFrames);
    },

    trimLayerOutFrames: function (layerId, deltaFrames) {
      return layerCall("trimLayerOutFrames", layerId, deltaFrames);
    }
  };
}(window));
