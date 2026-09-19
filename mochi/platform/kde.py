"""KDE Plasma: KWin runs kwin.js for us, which pushes window rects to this process over DBus."""
import json
import logging
import math
from pathlib import Path

from PySide6.QtCore import ClassInfo, QObject, Slot
from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage
from PySide6.QtWidgets import QApplication

from .base import Platform

log = logging.getLogger("mochi")
SERVICE, PATH, SCRIPT = "org.mochi.Pet", "/pet", "mochi"


def parse_windows(js):
    """kwin.js payload '[[id, x, y, w, h], ...]' -> {id: (x, y, w, h)}.
    Malformed entries are skipped; a payload that isn't a list raises ValueError/TypeError (rejected whole)."""
    wins = {}
    for e in json.loads(js):
        try:
            i, x, y, w, h = e
            if all(isinstance(v, (int, float)) and math.isfinite(v) for v in (x, y, w, h)) and w > 0 and h > 0:
                wins[i] = (x, y, w, h)
        except (ValueError, TypeError):
            pass
    return wins


@ClassInfo({"D-Bus Interface": SERVICE})
class Bus(QObject):
    """Receives window rects pushed by kwin.js (Wayland won't let a normal app list other windows)."""
    def __init__(self, on_windows):
        super().__init__()
        self.on_windows = on_windows

    @Slot(str)
    def windows(self, js):
        try:
            wins = parse_windows(js)
        except (ValueError, TypeError) as e:       # anyone on the session bus can call us; keep the last good list
            log.warning("ignored bad window payload: %s", e)
            return
        self.on_windows(wins)


class KdePlatform(Platform):
    def __init__(self, on_windows, sb):
        super().__init__(on_windows)
        self.sb, self.bus = sb, Bus(on_windows)

    def start(self):
        self.sb.registerObject(PATH, self.bus, QDBusConnection.ExportAllSlots)
        self.load_script()

    def load_script(self):
        # ponytail: KDE only; elsewhere the pet just walks on the screen floor
        kw = QDBusInterface("org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting", self.sb)
        if not kw.isValid():
            log.info("KWin not available: walking on the screen floor only")
            return
        kw.call("unloadScript", SCRIPT)                        # a crashed run may have left it loaded
        r = kw.call("loadScript", str(Path(__file__).with_name("kwin.js")), SCRIPT)
        args = r.arguments()
        if r.type() == QDBusMessage.MessageType.ErrorMessage or not args or args[0] < 0:
            log.error("KWin loadScript failed: %s", r.errorMessage() or args)
            return
        QApplication.instance().aboutToQuit.connect(lambda: kw.call("unloadScript", SCRIPT))
        r = QDBusInterface("org.kde.KWin", f"/Scripting/Script{args[0]}", "org.kde.kwin.Script", self.sb).call("run")
        if r.type() == QDBusMessage.MessageType.ErrorMessage:
            log.error("KWin script run failed: %s", r.errorMessage())
