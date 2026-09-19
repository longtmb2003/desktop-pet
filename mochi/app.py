"""Entry point: build the QApplication, the pet, and the platform integration."""
import argparse
import logging
import os
import signal
import sys

from . import __version__, autostart


def cli(argv):
    """handle `mochi autostart on|off|status`, `mochi pets` and `--version` without starting the GUI; True if it did"""
    ap = argparse.ArgumentParser(prog="mochi", description="Mochi: a tiny vector desktop pet (run without arguments to start it)")
    ap.add_argument("--version", action="version", version=f"mochi {__version__}")
    ap.add_argument("command", nargs="?", choices=["autostart", "pets"],
                    help="autostart: manage starting Mochi at login; pets: list the available characters")
    ap.add_argument("state", nargs="?", choices=["on", "off", "status"], default="status")
    args, _ = ap.parse_known_args(argv)                          # Qt may add its own options; leave them alone
    if args.command == "pets":
        from .pets import available
        for pid, d in available().items(): print(f"{pid:12s} {d.name} ({d.kind}, {d.size}px)")
        return True
    if args.command != "autostart": return False
    if args.state == "on": print("autostart on:", autostart.enable())
    elif args.state == "off": autostart.disable(); print("autostart off")
    else: print("autostart", "on" if autostart.is_enabled() else "off")
    return True


def main():
    if cli(sys.argv[1:]): return
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
    platform = detect(pet.set_windows, pet)
    platform.start()
    pet.show()
    sys.exit(app.exec())
