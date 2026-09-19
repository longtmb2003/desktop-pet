"""Tells the pet when the screen is locked and when the computer is about to sleep / has woken up.
Screen lock: `ActiveChanged` from org.freedesktop.ScreenSaver on the session bus (KDE and others). Suspend: `PrepareForSleep` from
systemd-logind on the system bus. Either may be missing (no such service): then that source is simply never heard from."""
import logging

from PySide6.QtCore import QObject, Slot
from PySide6.QtDBus import QDBusConnection, QDBusInterface

log = logging.getLogger("mochi")
SAVER = "org.freedesktop.ScreenSaver"
SAVER_PATHS = ("/org/freedesktop/ScreenSaver", "/ScreenSaver")
LOGIND = ("org.freedesktop.login1", "/org/freedesktop/login1", "org.freedesktop.login1.Manager")


class PowerWatcher(QObject):
    def __init__(self, on_lock, on_suspend, session=None, system=None):
        super().__init__()
        self.on_lock, self.on_suspend, self.connected = on_lock, on_suspend, []
        session = session or QDBusConnection.sessionBus()
        system = system or QDBusConnection.systemBus()
        for path in SAVER_PATHS:
            if session.isConnected() and session.connect("", path, SAVER, "ActiveChanged", self, "1screenActive(bool)"):
                self.connected.append(f"session:{path}")
        if system.isConnected() and system.connect(LOGIND[0], LOGIND[1], LOGIND[2], "PrepareForSleep", self, "1prepareForSleep(bool)"):
            self.connected.append("system:PrepareForSleep")
        if not self.connected: log.info("no lock/suspend notifications available: the pet won't sleep with the screen lock")
        self.on_lock(self.locked_now(session))

    @staticmethod
    def locked_now(session):
        """is the screen locked right now? (asked once at start, in case Mochi starts on a locked screen)"""
        if not session.isConnected(): return False
        r = QDBusInterface(SAVER, SAVER_PATHS[0], SAVER, session).call("GetActive")
        args = r.arguments()
        return bool(args[0]) if args and isinstance(args[0], bool) else False

    @Slot(bool)
    def screenActive(self, locked):                 # any session-bus process may send this: it only ever toggles a flag
        self.on_lock(bool(locked))

    @Slot(bool)
    def prepareForSleep(self, going_to_sleep):
        self.on_suspend(bool(going_to_sleep))
