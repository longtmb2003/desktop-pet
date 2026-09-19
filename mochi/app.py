"""Entry point: build the QApplication, the pet, and the platform integration."""
import logging
import os
import signal
import sys


def main():
    if os.environ.get("WAYLAND_DISPLAY"):
        os.environ.setdefault("QT_QPA_PLATFORM", "xcb")  # Wayland forbids self-positioning; XWayland allows it
    from PySide6.QtWidgets import QApplication

    from .pet import Pet
    from .platform import detect

    app = QApplication(sys.argv)
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(levelname)s: %(message)s")
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: app.quit())          # `kill` / Ctrl-C -> clean exit (unloads the KWin script)
    pet = Pet()
    platform = detect(pet.set_windows)
    platform.start()
    pet.show()
    sys.exit(app.exec())
