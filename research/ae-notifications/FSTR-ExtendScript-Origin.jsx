(function () {
    var p = app.project;
    var c = p ? p.activeItem : null;
    if (!(c instanceof CompItem) || c.numLayers < 1) {
        throw new Error("FSTR requires an active composition with at least one layer");
    }
    var source = c.selectedLayers.length ? c.selectedLayers[0] : c.layer(1);
    app.beginUndoGroup("FSTR ExtendScript Origin Matrix");
    var dupe = source.duplicate();
    dupe.moveToBeginning();
    dupe.startTime = dupe.startTime + c.frameDuration;
    dupe.enabled = !dupe.enabled;
    c.time = Math.min(Math.max(0, c.duration - c.frameDuration), c.time + c.frameDuration);
    dupe.remove();
    app.endUndoGroup();
    return "FSTR_EXTENDSCRIPT_ORIGIN_OK";
}());
