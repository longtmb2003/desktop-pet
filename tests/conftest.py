import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")     # before any Qt import: tests never touch the real desktop

import pytest  # noqa: E402
from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from mochi.pet import Pet
from mochi.pets import MOCHI  # noqa: E402
from mochi.settings import Settings  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pet(qapp, tmp_path):
    p = Pet(Settings(QSettings(str(tmp_path / "mochi.ini"), QSettings.IniFormat)), pets={"mochi": MOCHI})     # hermetic: no packs from disk
    p.timer.stop()                                          # tests drive tick() by hand
    p.clock.restart = lambda: 33                            # fixed 33 ms frames
    yield p
    p.close()


def write_pack(root, wide=False, **over):
    """a small valid sprite pack in `root` (an opaque blob as the body, ink dots as faces); `over` replaces pack.json keys"""
    import json

    from PySide6.QtGui import QColor, QImage, QPainter
    root.mkdir(parents=True, exist_ok=True); (root / "faces").mkdir(exist_ok=True)
    body = QImage(160, 80, QImage.Format_ARGB32) if wide else QImage(40, 80, QImage.Format_ARGB32)
    body.fill(0)
    p = QPainter(body); p.setBrush(QColor("#6a8caf"))
    if wide: p.drawRect(0, 0, body.width(), 80)                # a rectangle: its corners are the hard case for turning and leaning
    else: p.drawEllipse(2, 2, 36, 76)
    p.end(); body.save(str(root / "body.png"))
    for name in ("n", "t0", "t1", "l"):
        f = QImage(20, 10, QImage.Format_ARGB32); f.fill(0)
        q = QPainter(f); q.setBrush(QColor("black")); q.drawEllipse(2, 2, 5, 5); q.end()
        f.save(str(root / "faces" / f"{name}.png"))
    j = {"id": "blob", "name": "Blob", "size": 200, "feet": 190, "height": 150, "walk_speed": 30, "body": "body.png",
         "face": {"box": [10, 10, 20, 10]},
         "faces": {"neutral": ["faces/n.png"], "talk": ["faces/t0.png", "faces/t1.png"], "laugh": ["faces/l.png"]},
         "fps": {"talk": 10}, "behaviors": {"idle": 3, "walk": 2, "sleep": 1, "rant": 1}, "chatter": ["Bloop", "Hello"], "scream": "Waaah!"}
    j.update(over)
    (root / "pack.json").write_text(json.dumps(j), encoding="utf-8")
    return root
