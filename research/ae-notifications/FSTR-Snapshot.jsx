(function () {
    function clean(value) {
        return String(value).replace(/[|;\r\n]/g, "_");
    }
    function buildState() {
        var p = app.project;
        var c = p ? p.activeItem : null;
        if (!(c instanceof CompItem)) {
            return "NO_ACTIVE_COMP";
        }
        var parts = [];
        parts.push("comp=" + clean(c.name));
        parts.push("layers=" + c.numLayers);
        parts.push("time=" + c.time.toFixed(6));
        var selected = c.selectedLayers;
        var sel = [];
        for (var s = 0; s < selected.length; s++) sel.push(selected[s].index);
        parts.push("selected=" + sel.join(","));
        var limit = Math.min(c.numLayers, 8);
        for (var i = 1; i <= limit; i++) {
            var l = c.layer(i);
            var audio = "na";
            try { audio = l.audioEnabled ? "1" : "0"; } catch (_) {}
            parts.push(
                "L" + i + "=" + clean(l.name) + "," +
                l.startTime.toFixed(6) + "," + l.inPoint.toFixed(6) + "," +
                l.outPoint.toFixed(6) + "," + (l.enabled ? "1" : "0") + "," +
                (l.solo ? "1" : "0") + "," + (l.locked ? "1" : "0") + "," + audio
            );
        }
        return parts.join("|");
    }

    var scriptFile = new File($.fileName);
    var targetFile = new File(scriptFile.path + "/snapshot-target.txt");
    if (!targetFile.open("r")) {
        throw new Error("FSTR snapshot target file unavailable");
    }
    var outputPath = targetFile.read();
    targetFile.close();
    outputPath = String(outputPath).replace(/[\r\n]+$/g, "");
    if (!outputPath) {
        throw new Error("FSTR snapshot output path is empty");
    }

    var out = new File(outputPath);
    out.encoding = "UTF-8";
    if (!out.open("w")) {
        throw new Error("FSTR snapshot output cannot be opened");
    }
    out.write(buildState());
    out.close();
}());
