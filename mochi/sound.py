"""A short chime for the end of a Pomodoro phase, through whatever the desktop offers, else the terminal bell."""
import shutil

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QApplication

CHIMES = (("canberra-gtk-play", ["-i", "complete"]), ("paplay", ["/usr/share/sounds/freedesktop/stereo/complete.oga"]))


def chime():
    for prog, args in CHIMES:
        if shutil.which(prog):
            QProcess.startDetached(prog, args)
            return
    QApplication.beep()
