import logging
import sys
from collections.abc import Callable

from .base import Platform

log = logging.getLogger("mochi")


def detect(on_windows: Callable[[dict], None], pet=None) -> Platform:
    """Pick the window source for this desktop and enforce a single running instance."""
    if sys.platform == "win32":
        try:
            from .windows import WindowsPlatform
            return WindowsPlatform(on_windows, pet)
        except Exception as e:
            log.warning("Windows platform init error: %s (falling back to floor-only)", e)
            return Platform(on_windows)

    if sys.platform == "darwin":
        try:
            from .macos import MacPlatform
            return MacPlatform(on_windows, pet)
        except Exception as e:
            log.warning("macOS platform init error: %s (falling back to floor-only)", e)
            return Platform(on_windows)

    if sys.platform.startswith("linux"):
        try:
            from PySide6.QtDBus import QDBusConnection
            from .kde import SERVICE, KdePlatform
            sb = QDBusConnection.sessionBus()
            if not sb.isConnected():
                log.warning("no session bus: walking on the screen floor only")
                return Platform(on_windows)
            if not sb.registerService(SERVICE):
                sys.exit(f"mochi: already running ({SERVICE} is taken)")
            return KdePlatform(on_windows, sb, pet)
        except Exception as e:
            log.warning("Linux platform init error: %s (falling back to floor-only)", e)
            return Platform(on_windows)

    return Platform(on_windows)
