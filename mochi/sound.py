"""A short, gentle chime for reminders and the end of Pomodoro phases across Linux, Windows, and macOS."""
import os
import shutil
import sys

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QApplication

CHIMES = (
    ("canberra-gtk-play", ["-i", "bell"]),
    ("canberra-gtk-play", ["-i", "complete"]),
    ("paplay", ["/usr/share/sounds/freedesktop/stereo/bell.oga"]),
    ("paplay", ["/usr/share/sounds/freedesktop/stereo/complete.oga"]),
    ("pw-play", ["/usr/share/sounds/freedesktop/stereo/bell.oga"]),
)


def chime():
    """Play a gentle, subtle alert chime on whatever the OS provides."""
    if sys.platform == "win32":
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
            return
        except Exception:
            pass

    if sys.platform == "darwin":
        for sound_file in ("/System/Library/Sounds/Tink.aiff", "/System/Library/Sounds/Pop.aiff"):
            if os.path.exists(sound_file) and shutil.which("afplay"):
                QProcess.startDetached("afplay", [sound_file])
                return

    if sys.platform.startswith("linux"):
        for prog, args in CHIMES:
            if shutil.which(prog) and (not args or not args[-1].endswith(".oga") or os.path.exists(args[-1])):
                QProcess.startDetached(prog, args)
                return

    try:
        QApplication.beep()
    except Exception:
        pass
