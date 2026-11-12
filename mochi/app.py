"""Entry point: build the QApplication, the pet, and the platform integration."""
import argparse
import logging
import os
import signal
import sys

from . import __version__, autostart


def check_linux_gui_deps():
    if not sys.platform.startswith("linux"):
        return True
    if os.environ.get("QT_QPA_PLATFORM") in ("offscreen", "minimal"):
        return True
    import ctypes.util
    has_xcb_cursor = bool(
        ctypes.util.find_library("xcb-cursor")
        or any(os.path.exists(p) for p in (
            "/usr/lib/x86_64-linux-gnu/libxcb-cursor.so.0",
            "/usr/lib64/libxcb-cursor.so.0",
            "/usr/lib/libxcb-cursor.so.0",
            "/usr/lib/aarch64-linux-gnu/libxcb-cursor.so.0",
        ))
    )
    if os.environ.get("WAYLAND_DISPLAY"):
        if has_xcb_cursor:
            os.environ.setdefault("QT_QPA_PLATFORM", "xcb")  # Wayland forbids self-positioning; XWayland allows it
        else:
            logging.warning("libxcb-cursor0 not found: running on Wayland (floor-only mode). For window climbing, install: sudo apt install -y libxcb-cursor0")
        return True

    # On X11, Qt6 libqxcb.so strictly requires libxcb-cursor.so.0
    if not has_xcb_cursor:
        print(
            "\n[Mochi Error] Thiếu thư viện hệ thống 'libxcb-cursor0' (bắt buộc cho Qt6 trên Linux X11).\n"
            "Để Mochi có thể hiển thị cửa sổ, vui lòng chạy lệnh sau trên terminal:\n\n"
            "  Ubuntu / Debian:  sudo apt update && sudo apt install -y libxcb-cursor0 libxkbcommon-x11-0\n"
            "  Fedora:           sudo dnf install -y xcb-util-cursor libxkbcommon-x11\n"
            "  Arch Linux:       sudo pacman -S --noconfirm xcb-util-cursor libxkbcommon-x11\n",
            file=sys.stderr,
            flush=True,
        )
        return False
    return True


def cli(argv):
    """handle `mochi autostart on|off|status`, `mochi pets`, `-d/--daemon`, and `--version` without starting the GUI; True if it did"""
    ap = argparse.ArgumentParser(prog="mochi", description="Mochi: a tiny vector desktop pet (run without arguments to start it)")
    ap.add_argument("--version", action="version", version=f"mochi {__version__}")
    ap.add_argument("-d", "--daemon", action="store_true", help="chạy ngầm trong tiến trình background (giải phóng terminal)")
    ap.add_argument("command", nargs="?", choices=["autostart", "pets"],
                    help="autostart: manage starting Mochi at login; pets: list the available characters")
    ap.add_argument("state", nargs="?", choices=["on", "off", "status"], default="status")
    args, _ = ap.parse_known_args(argv)                          # Qt may add its own options; leave them alone

    if args.command == "pets":
        from .pets import available
        for pid, d in available().items(): print(f"{pid:12s} {d.name} ({d.kind}, {d.size}px)")
        return True
    if args.command == "autostart":
        if args.state == "on": print("autostart on:", autostart.enable())
        elif args.state == "off": autostart.disable(); print("autostart off")
        else: print("autostart", "on" if autostart.is_enabled() else "off")
        return True

    if not check_linux_gui_deps():
        sys.exit(1)

    if getattr(args, "daemon", False):
        if hasattr(os, "fork"):
            pid = os.fork()
            if pid > 0:
                print(f"Mochi đã được khởi chạy ngầm trong tiến trình (PID: {pid}).")
                print("Dừng Mochi bất cứ lúc nào bằng lệnh: pkill -x mochi")
                return True
            os.setsid()
    return False


def main():
    if cli(sys.argv[1:]): return
    # Prevent bundled glib from loading mismatched host GIO/GVFS modules
    for var in ("GIO_MODULE_DIR", "GTK_PATH", "GDK_PIXBUF_MODULE_FILE"):
        os.environ.pop(var, None)
    os.environ["GIO_MODULE_DIR"] = "/dev/null"
    from PySide6.QtWidgets import QApplication

    from .pet import Pet
    from .platform import detect

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(levelname)s: %(message)s")
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: app.quit())          # `kill` / Ctrl-C -> clean exit (unloads the KWin script)
    pet = Pet()
    platform = detect(pet.set_windows, pet)
    from .power import PowerWatcher
    pet.attach_power(PowerWatcher(pet.on_lock, pet.on_suspend))       # asleep while the screen is locked or the computer sleeps
    platform.start()
    pet.show()
    sys.exit(app.exec())
