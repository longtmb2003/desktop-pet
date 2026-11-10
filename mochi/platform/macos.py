"""macOS platform support: fetch top-level window positions and active window."""
import logging
import sys
from collections.abc import Callable

from PySide6.QtCore import QTimer

from .base import Platform

log = logging.getLogger("mochi")

POLL_MS = 600


class MacPlatform(Platform):
    def __init__(self, on_windows: Callable[[dict], None], pet=None):
        super().__init__(on_windows)
        self.pet = pet
        self.timer = None

    def start(self) -> None:
        self.timer = QTimer()
        self.timer.setInterval(POLL_MS)
        self.timer.timeout.connect(self.poll_windows)
        self.timer.start()
        self.poll_windows()

    def poll_windows(self) -> None:
        if sys.platform != "darwin":
            return
        try:
            import Quartz
            options = Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements
            win_list = Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID)
            windows = []
            for w in win_list:
                layer = w.get(Quartz.kCGWindowLayer, 0)
                if layer != 0:  # standard normal application windows have layer 0
                    continue
                bounds = w.get(Quartz.kCGWindowBounds)
                if not bounds:
                    continue
                wid = str(w.get(Quartz.kCGWindowNumber, ""))
                x = bounds.get("X", 0)
                y = bounds.get("Y", 0)
                width = bounds.get("Width", 0)
                height = bounds.get("Height", 0)
                if width > 80 and height > 80:
                    windows.append((wid, x, y, width, height))

            wins = {i: (x, y, w, h) for i, x, y, w, h in reversed(windows)}
            self.on_windows(wins)

            if self.pet is not None:
                from AppKit import NSWorkspace
                active_app = NSWorkspace.sharedWorkspace().frontmostApplication()
                if active_app:
                    app_name = active_app.localizedName() or ""
                    self.pet.set_active(str(active_app.processIdentifier()), app_name)
        except Exception as e:
            log.warning("macOS window enumeration error (using floor-only): %s", e)
            self.on_windows({})
