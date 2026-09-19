"""The items on the user's desktop folder (the icons you see on the desktop): what they are called, and opening one.
Mochi cannot know where each icon is drawn (KDE doesn't say), so it works with the folder's contents, not their positions."""
import os
from pathlib import Path

from .bubble import clean_text

MAX_ITEMS, MAX_NAME = 200, 40
MAX_READ = 16 * 1024                            # a .desktop file is tiny; never read more than this


def desktop_dir():
    """the desktop folder (XDG, e.g. ~/Desktop or ~/Màn hình nền); overridable with MOCHI_DESKTOP for tests"""
    env = os.environ.get("MOCHI_DESKTOP")
    if env: return Path(env)
    from PySide6.QtCore import QStandardPaths
    return Path(QStandardPaths.writableLocation(QStandardPaths.DesktopLocation) or Path.home() / "Desktop")


def entry_name(path):
    """what an item is called: a launcher's Name= for .desktop files, else the file name without its extension"""
    p = Path(path)
    if p.suffix == ".desktop":
        try:
            with open(p, encoding="utf-8", errors="replace") as f: text = f.read(MAX_READ)
            in_entry = False
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("["): in_entry = line == "[Desktop Entry]"
                elif in_entry and line.startswith("Name="):
                    name = clean_text(line[5:])[:MAX_NAME]
                    if name: return name
        except OSError:
            pass
    return clean_text(p.stem if p.suffix else p.name)[:MAX_NAME] or p.name[:MAX_NAME]


def items(directory=None):
    """[(path, name)] of the visible things on the desktop, sorted by name; never raises (no folder means no items)"""
    d = Path(directory) if directory else desktop_dir()
    try:
        entries = [e for e in sorted(d.iterdir(), key=lambda e: e.name.lower()) if not e.name.startswith(".")]
    except OSError:
        return []
    return [(e, entry_name(e)) for e in entries[:MAX_ITEMS]]


def is_on_desktop(path, directory=None):
    """is `path` directly inside the desktop folder? (the only things Mochi will open)"""
    d = (Path(directory) if directory else desktop_dir())
    try:
        return Path(path).parent.resolve() == d.resolve() and Path(path).name in {e.name for e, _ in items(d)}
    except OSError:
        return False


def summary(names):
    """the text a reaction uses for one or more dropped things"""
    names = [clean_text(n)[:MAX_NAME] for n in names if clean_text(n)]
    if not names: return "cái gì đó"
    return names[0] if len(names) == 1 else f"{len(names)} thứ"
