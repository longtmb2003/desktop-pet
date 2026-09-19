import logging
import sys
from collections.abc import Callable

from .base import Platform

log = logging.getLogger("mochi")


def detect(on_windows: Callable[[dict], None]) -> Platform:
    """Pick the window source for this desktop and enforce a single running instance (via the DBus name)."""
    if not sys.platform.startswith("linux"):
        return Platform(on_windows)
    from PySide6.QtDBus import QDBusConnection

    from .kde import SERVICE, KdePlatform
    sb = QDBusConnection.sessionBus()
    if not sb.isConnected():
        log.warning("no session bus: walking on the screen floor only")
        return Platform(on_windows)
    if not sb.registerService(SERVICE):
        sys.exit(f"mochi: already running ({SERVICE} is taken)")
    return KdePlatform(on_windows, sb)
