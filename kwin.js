// Loaded into KWin by pet.py: pushes the rects of visible normal windows to the pet over DBus.
function visible(w) {
    return w.normalWindow && !w.minimized && !w.fullScreen &&
        (w.desktops.length === 0 || w.desktops.indexOf(workspace.currentDesktop) >= 0);
}
let last = "";
function push(skip) {
    const rects = workspace.windowList().filter(w => w !== skip && visible(w)).map(w => {
        const g = w.frameGeometry;
        return [String(w.internalId), Math.round(g.x), Math.round(g.y), Math.round(g.width), Math.round(g.height)];
    });
    const s = JSON.stringify(rects);
    if (s === last) return;
    last = s;
    callDBus("org.mochi.Pet", "/pet", "org.mochi.Pet", "windows", s);
}
function hook(w) {
    if (w.normalWindow) {
        w.frameGeometryChanged.connect(push);
        w.minimizedChanged.connect(push);
        w.desktopsChanged.connect(push);
    }
    push();
}
workspace.windowList().forEach(hook);
workspace.windowAdded.connect(hook);
workspace.windowRemoved.connect(push);
workspace.currentDesktopChanged.connect(push);
