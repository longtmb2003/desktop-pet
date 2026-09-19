import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")     # before any Qt import: tests never touch the real desktop

import pytest  # noqa: E402
from PySide6.QtCore import QPoint, QSettings, Qt  # noqa: E402
from PySide6.QtGui import QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from mochi.pet import Pet
from mochi.pets import MOCHI  # noqa: E402
from mochi.pets.pack import load_dir  # noqa: E402
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


def write_pack(root, wide=False, nose=False, **over):
    """a small valid sprite pack in `root` (an opaque blob as the body, ink dots as faces); `over` replaces pack.json keys"""
    import json

    from PySide6.QtGui import QColor, QImage, QPainter
    root.mkdir(parents=True, exist_ok=True); (root / "faces").mkdir(exist_ok=True)
    body = QImage(160, 80, QImage.Format_ARGB32) if wide else QImage(40, 80, QImage.Format_ARGB32)
    body.fill(0)
    p = QPainter(body); p.setBrush(QColor("#6a8caf"))
    if wide: p.drawRect(0, 0, body.width(), 80)                # a rectangle: its corners are the hard case for turning and leaning
    else: p.drawEllipse(2, 2, 36, 76)
    if nose: p.setBrush(QColor("#c0392b")); p.drawRect(body.width() - 10, 30, 10, 12)      # a nose on the right: the art looks right
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


@pytest.fixture(autouse=True)
def no_real_desktop(tmp_path, monkeypatch):
    """tests never look at (or open things from) the real desktop folder"""
    monkeypatch.setenv("MOCHI_DESKTOP", str(tmp_path / "desktop"))


class Afternoon:
    """stands in for datetime in mochi.pet: it is always Monday 15:00, so no test depends on when it happens to run (the pet
    sleeps at midday and at night, and is calmer in the evening)"""
    @staticmethod
    def now(tz=None):
        from datetime import datetime
        return datetime(2026, 9, 21, 15, 0, 0)


@pytest.fixture(autouse=True)
def fixed_time_of_day(monkeypatch):
    import mochi.pet
    monkeypatch.setattr(mochi.pet, "datetime", Afternoon)


HANHAN = Path(__file__).resolve().parent.parent / "mochi" / "pets" / "packs" / "hanhan"


@pytest.fixture
def pets(qapp, tmp_path):
    return {"mochi": MOCHI, "blob": load_dir(write_pack(tmp_path / "pack"))}


@pytest.fixture
def make(qapp, tmp_path, pets):
    made = []

    def build(pet="blob", scale=1.0, pets=pets):
        cfg = Settings(QSettings(str(tmp_path / f"s{len(made)}.ini"), QSettings.IniFormat)); cfg.pet, cfg.scale = pet, scale
        p = Pet(cfg, pets); p.timer.stop(); p.clock.restart = lambda: 33
        made.append(p)
        return p
    yield build
    for p in made: p.close()



def uncovered_and_clipped(p):
    """(strongest visible pixel outside the click mask, strongest visible pixel on the window edge), as alpha values, for what the
    pet paints now. Done with image operations, not a Python loop over pixels, so a sweep of poses stays fast."""
    n = p.size
    p.mask_key = None; p.update_mask(); m = p.mask(); p.clearMask()
    img = QImage(n, n, QImage.Format_ARGB32); img.fill(0)
    pt = QPainter(img); p.render(pt, QPoint(0, 0)); pt.end()
    a = bytes(img.constBits())[3::4]
    edge = max(max(a[:n]), max(a[-n:]), max(a[::n]), max(a[n - 1::n]))
    q = QPainter(img); q.setClipRegion(m); q.setCompositionMode(QPainter.CompositionMode_DestinationOut)
    q.fillRect(img.rect(), Qt.black); q.end()
    return max(bytes(img.constBits())[3::4]), edge                       # what remains after erasing everything the mask covers



def render(p):
    from PySide6.QtCore import QPoint
    img = QImage(p.size, p.size, QImage.Format_ARGB32); img.fill(0)
    pt = QPainter(img); p.render(pt, QPoint(0, 0)); pt.end()
    return img


