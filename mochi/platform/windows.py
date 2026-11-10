"""Windows platform support: fetch top-level window positions and active window using ctypes and Win32 APIs."""
import ctypes
import logging
import sys
from collections.abc import Callable

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication

from .base import Platform

log = logging.getLogger("mochi")

POLL_MS = 500
DWMWA_CLOAKED = 14
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
ERROR_ALREADY_EXISTS = 183

SKIP_CLASSES = {
    "Progman",
    "WorkerW",
    "Shell_TrayWnd",
    "Shell_SecondaryTrayWnd",
    "Windows.UI.Core.CoreWindow",
}


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


def single_instance_check():
    """Ensure only one instance runs on Windows using a named mutex."""
    if sys.platform != "win32":
        return None
    try:
        kernel32 = ctypes.windll.kernel32
        mutex = kernel32.CreateMutexW(None, True, "Global\\MochiDesktopPetMutex")
        if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            sys.exit("mochi: already running (Windows single instance mutex held)")
        return mutex
    except Exception as e:
        log.warning("could not create single instance mutex: %s", e)
        return None


class WindowsPlatform(Platform):
    def __init__(self, on_windows: Callable[[dict], None], pet=None):
        super().__init__(on_windows)
        self.pet = pet
        self.timer = None
        self.mutex = single_instance_check()

    def start(self) -> None:
        self.timer = QTimer()
        self.timer.setInterval(POLL_MS)
        self.timer.timeout.connect(self.poll_windows)
        self.timer.start()
        self.poll_windows()

    def poll_windows(self) -> None:
        if sys.platform != "win32":
            return
        user32 = ctypes.windll.user32
        dwmapi = getattr(ctypes.windll, "dwmapi", None)

        windows = []

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def enum_cb(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            if user32.IsIconic(hwnd):
                return True

            if dwmapi and hasattr(dwmapi, "DwmGetWindowAttribute"):
                cloaked = ctypes.c_int(0)
                res = dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
                if res == 0 and cloaked.value != 0:
                    return True

            ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if ex_style & WS_EX_TOOLWINDOW:
                return True

            buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, buf, 256)
            cls_name = buf.value
            if cls_name in SKIP_CLASSES:
                return True

            rect = RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            if w > 80 and h > 80:
                windows.append((str(hwnd), rect.left, rect.top, w, h))
            return True

        cb = WNDENUMPROC(enum_cb)
        user32.EnumWindows(cb, 0)

        # EnumWindows returns top-to-bottom; Mochi expects bottom-to-top
        wins = {i: (x, y, w, h) for i, x, y, w, h in reversed(windows)}
        self.on_windows(wins)

        # Active window and fullscreen detection
        if self.pet is not None:
            active_hwnd = user32.GetForegroundWindow()
            if active_hwnd:
                buf = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(active_hwnd, buf, 256)
                cls_name = buf.value
                self.pet.set_active(str(active_hwnd), cls_name)

                # Fullscreen detection
                rect = RECT()
                user32.GetWindowRect(active_hwnd, ctypes.byref(rect))
                scr = QGuiApplication.primaryScreen().geometry()
                is_fs = (
                    rect.left <= scr.left()
                    and rect.top <= scr.top()
                    and rect.right >= scr.right()
                    and rect.bottom >= scr.bottom()
                )
                self.pet.fullscreen = is_fs
