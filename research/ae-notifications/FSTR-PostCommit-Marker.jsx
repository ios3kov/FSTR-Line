(function () {
    function nowMs() { return (new Date()).getTime(); }
    function writeLine(file, text) {
        file.writeln(text);
        file.flush();
    }
    var scriptFile = new File($.fileName);
    var targetFile = new File(scriptFile.path + "/marker-target.txt");
    if (!targetFile.open("r")) throw new Error("FSTR marker target unavailable");
    var outputPath = String(targetFile.read()).replace(/[\r\n]+$/g, "");
    targetFile.close();
    if (!outputPath) throw new Error("FSTR marker output path empty");
    var out = new File(outputPath);
    out.encoding = "UTF-8";
    if (!out.open("w")) throw new Error("FSTR marker output cannot be opened");

    var p = app.project;
    var c = p ? p.activeItem : null;
    if (!(c instanceof CompItem) || c.numLayers < 1) {
        writeLine(out, "ERROR|" + nowMs() + "|NO_ACTIVE_COMP_OR_LAYER");
        out.close();
        throw new Error("FSTR needs active comp with a layer");
    }
    var l = c.selectedLayers.length ? c.selectedLayers[0] : c.layer(1);
    writeLine(out, "before|" + nowMs() + "|enabled=" + (l.enabled ? "1" : "0"));
    app.beginUndoGroup("FSTR PostCommit Marker");
    l.enabled = !l.enabled;
    writeLine(out, "after-mutation|" + nowMs() + "|enabled=" + (l.enabled ? "1" : "0"));
    app.endUndoGroup();
    writeLine(out, "after-end-undo|" + nowMs() + "|enabled=" + (l.enabled ? "1" : "0"));
    out.close();
}());
