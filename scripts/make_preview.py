"""Render docs/preview.png: every theme in a few poses, drawn by the pet's own renderer (run from anywhere)."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # so `mochi` imports when run as a script
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from mochi.pet import Pet  # noqa: E402
from mochi.physics import S  # noqa: E402
from mochi.renderer import THEMES, paint  # noqa: E402
from mochi.state import Action, Expression, Motion, State  # noqa: E402

POSES = [("idle", State()), ("happy", State(expression=Expression.HAPPY)), ("sleep", State(Motion.SLEEP)),
         ("yawn", State(action=Action.YAWN)), ("stretch", State(action=Action.STRETCH)), ("groom", State(action=Action.GROOM)),
         ("dizzy", State(Motion.WALK, Expression.DIZZY))]
LABEL, HEAD = 84, 26

app = QApplication([])
pet = Pet(); pet.timer.stop(); pet.move(-S // 2, -100)          # cursor at the window centre: eyes look straight ahead
pet.facing, pet.grounded, pet.dur = 1, True, 2.0
img = QImage(LABEL + S * len(THEMES), HEAD + S * len(POSES), QImage.Format_ARGB32); img.fill(QColor("#fbf7f4"))
p = QPainter(img); p.setRenderHint(QPainter.Antialiasing); p.setPen(QColor("#6b5560"))
for c, theme in enumerate(THEMES):
    p.drawText(QRectF(LABEL + c * S, 0, S, HEAD), Qt.AlignCenter, theme)
    for r, (name, state) in enumerate(POSES):
        pet.theme, pet.state, pet.t, pet.began = theme, state, 10.0, 9.0            # mid-way through a one-shot pose
        pet.hearts = [[-24 + 16 * j, -100 - 6 * j, 1.0] for j in range(4)] if name == "happy" else []
        cell = QImage(S, S, QImage.Format_ARGB32); cell.fill(0)       # own canvas: paint() resets the transform for hearts/zzz
        cp = QPainter(cell); cp.setRenderHint(QPainter.Antialiasing); paint(pet, cp); cp.end()
        p.drawImage(LABEL + c * S, HEAD + r * S, cell)
        if c == 0: p.drawText(QRectF(0, HEAD + r * S, LABEL, S), Qt.AlignCenter, name)
p.end()
docs = Path(__file__).resolve().parent.parent / "docs"
img.save(str(docs / "preview.png"))

# the newer poses (one theme, two rows): things only some situations show
EXTRA = [("scared", State(Motion.AIRBORNE, Expression.SCARED), dict(grounded=False)), ("work", State(action=Action.WORK), {}),
         ("push", State(Motion.WALK, action=Action.PUSH), {}), ("flip", State(action=Action.FLIP), dict(grounded=False)),
         ("tired", State(), dict(hot=True)), ("happy", State(expression=Expression.HAPPY), {})]
sheet = QImage(S * 3, (S + 24) * 2, QImage.Format_ARGB32); sheet.fill(QColor("#fbf7f4"))
q = QPainter(sheet); q.setRenderHint(QPainter.Antialiasing); q.setPen(QColor("#6b5560"))
for i, (name, state, extra) in enumerate(EXTRA):
    began = 9.55 if name == "flip" else 9.0
    pet.theme, pet.state, pet.t, pet.began, pet.hearts, pet.hot, pet.grounded = "Kem", state, 10.0, began, [], False, True
    if name == "flip": pet.dur = 0.55
    for k, v in extra.items(): setattr(pet, k, v)
    cell = QImage(S, S, QImage.Format_ARGB32); cell.fill(0)
    cp = QPainter(cell); cp.setRenderHint(QPainter.Antialiasing); paint(pet, cp); cp.end()
    x, y = (i % 3) * S, (i // 3) * (S + 24)
    q.drawImage(x, y, cell); q.drawText(QRectF(x, y + S - 6, S, 24), Qt.AlignCenter, name)
    pet.dur = 2.0
q.end()
sheet.save(str(docs / "poses.png"))
print("wrote docs/preview.png, docs/poses.png")
