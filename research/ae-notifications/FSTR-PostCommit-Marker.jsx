(function () {
    function nowMs() { return (new Date()).getTime(); }
    function writeAll(path, lines) {
        var out = new File(path);
        out.encoding = "UTF-8";
        if (!out.open("w")) throw new Error("FSTR marker output cannot be opened");
        for (var i = 0; i < lines.length; i++) out.writeln(lines[i]);
        out.close();
    }

    var scriptFile = new File($.fileName);
    var targetFile = new File(scriptFile.path + "/marker-target.txt");
    if (!targetFile.open("r")) throw new Error("FSTR marker target unavailable");
    var outputPath = String(targetFile.read()).replace(/[\r\n]+$/g, "");
    targetFile.close();
    if (!outputPath) throw new Error("FSTR marker output path empty");

    var lines = [];
    var p = app.project;
    var c = p ? p.activeItem : null;
    if (!(c instanceof CompItem) || c.numLayers < 1) {
        lines.push("ERROR|" + nowMs() + "|NO_ACTIVE_COMP_OR_LAYER");
        writeAll(outputPath, lines);
        throw new Error("FSTR needs active comp with a layer");
    }

    var l = c.selectedLayers.length ? c.selectedLayers[0] : c.layer(1);
    lines.push("before|" + nowMs() + "|enabled=" + (l.enabled ? "1" : "0"));
    app.beginUndoGroup("FSTR PostCommit Marker");
    try {
        l.enabled = !l.enabled;
        lines.push("after-mutation|" + nowMs() + "|enabled=" + (l.enabled ? "1" : "0"));
    } finally {
        app.endUndoGroup();
    }
    lines.push("after-end-undo|" + nowMs() + "|enabled=" + (l.enabled ? "1" : "0"));
    writeAll(outputPath, lines);
}());
