"""Arms and hands for a character: a smooth tapered sleeve, a wrist cuff, and a five-fingered hand.
Drawn onto whatever QPainter it is given."""
import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainterPath, QPen

OUTLINE = QColor(28, 30, 38)
SKIN = QColor(247, 203, 160)
CUFF = QColor(244, 241, 232)                   # light cream/white inner sleeve showing at wrist

# each digit: (base x, base y, angle in degrees, length, width) in the hand's own frame: +x runs along the forearm, the wrist is at 0
DIGITS = {
    "point": (("thumb", 5, -5.5, -35, 6, 4.6), ("index", 10, -3, 0, 16, 4.4), ("middle", 10, -0.5, 0, 3.8, 4.4),
              ("ring", 10, 2, 0, 3.6, 4.2), ("pinky", 9.5, 4.2, 0, 3.2, 3.8)),              # index out, the rest curled into the palm
    "open": (("thumb", 4, -6, -62, 8, 4.6), ("index", 10, -3.5, -18, 11, 4.4), ("middle", 11, -1, -6, 13, 4.4),
             ("ring", 11, 1.5, 6, 12, 4.2), ("pinky", 10, 4, 20, 9, 3.8)),                   # fingers spread
    "grip": (("thumb", 6, -5, -15, 8, 4.6), ("index", 11, -3.6, 0, 5, 4.4), ("middle", 11.5, -1.2, 0, 5.5, 4.4),
             ("ring", 11, 1.3, 0, 5, 4.2), ("pinky", 10, 3.6, 0, 4.2, 3.8)),                  # closed round something it holds
}


def two_link(shoulder, target, l1, l2):
    """(elbow, wrist) for an arm of segments `l1` and `l2` from `shoulder` reaching for `target`. Out of reach it stretches
    straight towards it; too close it folds. The elbow bends downwards, or outwards (away from x = 0, the body's middle) for an
    arm that hangs straight, like a relaxed arm."""
    d = target - shoulder
    dist = math.hypot(d.x(), d.y())
    if dist < 1e-6: d, dist = QPointF(0, 1), 1.0
    u = d / dist
    reach = max(abs(l1 - l2) + 0.5, min(dist, l1 + l2 - 0.5))
    a = (l1 * l1 - l2 * l2 + reach * reach) / (2 * reach)
    h = math.sqrt(max(0.0, l1 * l1 - a * a))
    base, perp = shoulder + u * a, QPointF(-u.y(), u.x())
    one, two = base + perp * h, base - perp * h
    if abs(one.y() - two.y()) > 12: elbow = one if one.y() > two.y() else two          # the lower one ...
    else: elbow = one if abs(one.x()) > abs(two.x()) else two                           # ... or, for an arm hanging straight, the outer one
    return elbow, shoulder + u * reach


def _capsule(p, a, b, width, fill):
    p.setPen(QPen(OUTLINE, width + 1.0, Qt.SolidLine, Qt.RoundCap)); p.drawLine(a, b)
    p.setPen(QPen(fill, width, Qt.SolidLine, Qt.RoundCap)); p.drawLine(a, b)


def draw_hand(p, wrist, angle, kind="open", size=1.0):
    """a hand with a palm, a thumb and four fingers, at `wrist`, its fingers pointing along `angle` (radians). kind: "point" (index
    out, the others curled), "open" (all five spread) or "grip" (closed round an object)"""
    p.save(); p.translate(wrist); p.rotate(math.degrees(angle)); p.scale(size, size)
    digits = DIGITS[kind]
    order = digits[1:] + digits[:1] if kind == "grip" else digits                    # (a gripping thumb goes over the fingers)
    for _name, bx, by, ang, ln, w in (d for d in order if d[0] != "thumb" or kind != "grip"):
        r = math.radians(ang)
        _capsule(p, QPointF(bx, by), QPointF(bx + math.cos(r) * ln, by + math.sin(r) * ln), w, SKIN)
    p.setPen(QPen(OUTLINE, 1.0)); p.setBrush(SKIN); p.drawEllipse(QPointF(6, 0), 7.2, 6.4)   # the palm covers the finger bases
    if kind == "grip":
        _name, bx, by, ang, ln, w = digits[0]
        r = math.radians(ang)
        _capsule(p, QPointF(bx, by), QPointF(bx + math.cos(r) * ln, by + math.sin(r) * ln), w, SKIN)
    p.restore()


def draw_arm(p, coat, shoulder, target, width, kind="open", l1=36.0, l2=34.0, hand_size=None):
    """a smooth tapered sleeved arm from `shoulder` to a hand at `target`: one continuous sleeve tapering towards the wrist,
    a cream cuff, then the hand. Returns the wrist and the elbow."""
    elbow, wrist = two_link(shoulder, target, l1, l2)
    mid = (shoulder + wrist) * 0.5
    control = mid + (elbow - mid) * 0.5

    n_samples = 16
    pts_left = []
    pts_right = []
    u_last = QPointF(1, 0)

    for i in range(n_samples):
        t = i / (n_samples - 1)
        om = 1.0 - t
        pt = shoulder * (om * om) + control * (2.0 * om * t) + wrist * (t * t)
        d = (control - shoulder) * (2.0 * om) + (wrist - control) * (2.0 * t)
        dist = math.hypot(d.x(), d.y())
        if dist > 1e-6:
            u_last = d / dist
        norm = QPointF(-u_last.y(), u_last.x())
        hw = (width * 0.5) * (1.0 - 0.45 * t)
        pts_left.append(pt + norm * hw)
        pts_right.append(pt - norm * hw)

    sleeve_path = QPainterPath()
    sleeve_path.moveTo(pts_left[0])
    for pt in pts_left[1:]:
        sleeve_path.lineTo(pt)
    for pt in reversed(pts_right):
        sleeve_path.lineTo(pt)
    sleeve_path.closeSubpath()

    p.setPen(QPen(OUTLINE, 1.2, Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin))
    p.setBrush(coat)
    p.drawPath(sleeve_path)

    fold_path = QPainterPath()
    i_start = int(0.25 * (n_samples - 1))
    i_end = int(0.70 * (n_samples - 1))
    for i in range(i_start, i_end + 1):
        t = i / (n_samples - 1)
        om = 1.0 - t
        pt = shoulder * (om * om) + control * (2.0 * om * t) + wrist * (t * t)
        d = (control - shoulder) * (2.0 * om) + (wrist - control) * (2.0 * t)
        dist = math.hypot(d.x(), d.y())
        u = d / dist if dist > 1e-6 else u_last
        norm = QPointF(-u.y(), u.x())
        hw = (width * 0.5) * (1.0 - 0.45 * t)
        fold_pt = pt - norm * (0.3 * hw)
        if i == i_start:
            fold_path.moveTo(fold_pt)
        else:
            fold_path.lineTo(fold_pt)
    p.setPen(QPen(coat.darker(120), 1.0))
    p.setBrush(Qt.NoBrush)
    p.drawPath(fold_path)

    hw_wrist = (width * 0.5) * 0.55
    hw_cuff = hw_wrist * 1.10
    norm_wrist = QPointF(-u_last.y(), u_last.x())
    cuff_base = wrist - u_last * 4.0
    cuff_top = wrist + u_last * 4.0

    cuff_path = QPainterPath()
    cuff_path.moveTo(cuff_base + norm_wrist * hw_cuff)
    cuff_path.lineTo(cuff_top + norm_wrist * hw_cuff)
    cuff_path.lineTo(cuff_top - norm_wrist * hw_cuff)
    cuff_path.lineTo(cuff_base - norm_wrist * hw_cuff)
    cuff_path.closeSubpath()

    p.setPen(QPen(OUTLINE, 1.0))
    p.setBrush(CUFF)
    p.drawPath(cuff_path)

    draw_hand(p, wrist, math.atan2(u_last.y(), u_last.x()), kind, size=hand_size or max(0.7, width / 18))
    return wrist, elbow
