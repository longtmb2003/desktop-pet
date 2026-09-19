"""Render packaging/mochi.png from the pet's own renderer (run from the repo root; only needed when the look changes)."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # so `mochi` imports when run as a script
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtGui import QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from mochi.pet import Pet  # noqa: E402
from mochi.renderer import paint  # noqa: E402

app = QApplication([])
pet = Pet(); pet.timer.stop(); pet.move(0, 0)
pet.grounded, pet.facing, pet.t = False, 1, 0.0              # no floor shadow, eyes forward
img = QImage(256, 256, QImage.Format_ARGB32); img.fill(0)
p = QPainter(img)
p.setRenderHint(QPainter.Antialiasing); p.setRenderHint(QPainter.SmoothPixmapTransform)
k = 256 / 140
p.scale(k, k); p.translate(4, -31)                              # square crop of the 160x160 window around the pet's body
paint(pet, p)
p.end()
img.save("packaging/mochi.png")
print("wrote packaging/mochi.png")
