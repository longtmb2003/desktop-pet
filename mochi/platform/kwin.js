// Loaded into KWin by pet.py: pushes the rects of visible normal windows (bottom -> top) to the pet over DBus.
function visible(w) {
    return w.normalWindow && !w.minimized && !w.fullScreen &&
        (w.desktops.length === 0 || w.desktops.indexOf(workspace.currentDesktop) >= 0);
}
let last = "", lastFs = null;
function pushFullscreen() {                        // Quiet Mode: is any normal window fullscreen on the current desktop?
    const fs = workspace.stackingOrder.some(w => w.normalWindow && w.fullScreen && !w.minimized &&
        (w.desktops.length === 0 || w.desktops.indexOf(workspace.currentDesktop) >= 0));
    if (fs === lastFs) return;
    lastFs = fs;
    callDBus("org.mochi.Pet", "/pet", "org.mochi.Pet", "fullscreen", fs);
}
function push(skip) {
    pushFullscreen();
    const rects = workspace.stackingOrder.filter(w => w !== skip && visible(w)).map(w => {
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
        w.fullScreenChanged.connect(push);
    }
    push();
}
workspace.windowList().forEach(hook);
workspace.windowAdded.connect(hook);
workspace.windowRemoved.connect(push);
workspace.currentDesktopChanged.connect(push);
workspace.windowActivated.connect(() => push());   // raising a window changes the stacking order
