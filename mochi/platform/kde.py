"""KDE Plasma: KWin runs kwin.js for us, which pushes window rects to this process over DBus."""
import json
import logging
import math
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import ClassInfo, Slot
from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage
from PySide6.QtWidgets import QApplication

from ..api import PATH, SERVICE, Api
from .base import Platform

log = logging.getLogger("mochi")
SCRIPT = "mochi"
WARN_EVERY = 10.0                   # seconds between "bad payload" warnings: a noisy sender must not flood the log


def parse_windows(js):
    """kwin.js payload '[[id, x, y, w, h], ...]' -> {id: (x, y, w, h)}.
    Malformed entries are skipped; a payload that isn't a list raises TypeError, bad JSON ValueError (rejected whole)."""
    data = json.loads(js)
    if not isinstance(data, list):
        raise TypeError(f"expected a list of windows, got {type(data).__name__}")
    wins = {}
    for e in data:
        try:
            i, x, y, w, h = e
            if all(isinstance(v, (int, float)) and math.isfinite(v) for v in (x, y, w, h)) and w > 0 and h > 0:
                wins[i] = (x, y, w, h)
        except (ValueError, TypeError, OverflowError):        # OverflowError: an int too big for float, e.g. 1 followed by 400 digits
            pass
    return wins


_class_info: Any = ClassInfo                       # PySide6's type stubs declare ClassInfo without arguments


@_class_info({"D-Bus Interface": SERVICE})
class Bus(Api):
    """The pet's DBus object: the public API (see api.py) plus what kwin.js pushes at us (Wayland won't let a normal app list
    other windows, so KWin does it for us)."""
    def __init__(self, on_windows, pet=None):
        super().__init__(pet)
        self.on_windows, self.last_warn, self.dropped = on_windows, -WARN_EVERY, 0

    @Slot(bool)
    def fullscreen(self, on):
        if self.pet is not None: self.pet.fullscreen = bool(on)        # only ever a flag: Quiet Mode may follow it, nothing else

    @Slot(str)
    def windows(self, js):
        try:
            wins = parse_windows(js)
        except Exception as e:                     # untrusted input (anyone on the session bus can call us): never let it out of the slot
            now, self.dropped = time.monotonic(), self.dropped + 1
            if now - self.last_warn >= WARN_EVERY:
                log.warning("ignored bad window payload: %s (%d since the last warning)", e, self.dropped)
                self.last_warn, self.dropped = now, 0
            return
        self.on_windows(wins)


class KdePlatform(Platform):
    def __init__(self, on_windows, sb, pet=None):
        super().__init__(on_windows)
        self.sb, self.bus = sb, Bus(on_windows, pet)

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
