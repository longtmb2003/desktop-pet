"""Start Mochi at login through an XDG autostart entry (works on KDE and most other Linux desktops)."""
import os
import sys
from pathlib import Path

_RESERVED = set(" \t\n\"'\\><~|&;$*?#()`")
_ROOT = Path(__file__).resolve().parent.parent           # repo root when running from source


def quote_exec(arg):
    """quote one argument for a Desktop Entry `Exec=` value (spec: double quotes, then a second layer of \\ escaping)"""
    if not any(c in _RESERVED for c in arg): return arg
    for c in '\\"`$': arg = arg.replace(c, "\\" + c)
    return ('"' + arg + '"').replace("\\", "\\\\")


def entry_path():
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "autostart" / "mochi.desktop"


def entry_text():
    frozen = getattr(sys, "frozen", False)                # a PyInstaller build is one executable, else `python -m mochi`
    cmd = [sys.executable] if frozen else [sys.executable, "-m", "mochi"]
    lines = ["[Desktop Entry]", "Type=Application", "Name=Mochi", "Comment=A tiny vector desktop pet",
             "Exec=" + " ".join(quote_exec(a) for a in cmd)]
    if not frozen: lines.append("Path=" + str(_ROOT))     # so `-m mochi` finds the package
    lines += ["Icon=mochi", "Terminal=false", "X-KDE-autostart-after=panel", ""]
    return "\n".join(lines)


def enable():
    p = entry_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(entry_text(), encoding="utf-8")
    return p


def disable():
    entry_path().unlink(missing_ok=True)


def is_enabled():
    return entry_path().exists()
