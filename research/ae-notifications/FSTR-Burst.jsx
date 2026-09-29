(function () {
    var p = app.project;
    var c = p ? p.activeItem : null;
    if (!(c instanceof CompItem) || c.numLayers < 1) {
        throw new Error("FSTR requires an active composition with at least one layer");
    }
    var l = c.selectedLayers.length ? c.selectedLayers[0] : c.layer(1);
    var original = l.enabled;
    app.beginUndoGroup("FSTR Burst");
    for (var i = 0; i < 20; i++) {
        l.enabled = !l.enabled;
    }
    if (l.enabled !== original) l.enabled = original;
    app.endUndoGroup();
    return "FSTR_BURST_OK|20";
}());
