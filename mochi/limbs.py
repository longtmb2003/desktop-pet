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


def _along(shoulder, control, wrist, t):
    """(point, unit tangent) at parameter t of the quadratic curve shoulder -> wrist bending towards `control`"""
    om = 1.0 - t
    pt = shoulder * (om * om) + control * (2.0 * om * t) + wrist * (t * t)
    d = (control - shoulder) * (2.0 * om) + (wrist - control) * (2.0 * t)
    n = math.hypot(d.x(), d.y())
    return pt, (d / n if n > 1e-6 else QPointF(1, 0))


def draw_arm(p, coat, shoulder, target, width, kind="open", l1=36.0, l2=34.0, hand_size=None):
    """a smooth tapered sleeved arm from `shoulder` to a hand at `target`: one continuous sleeve tapering towards the wrist with a
    gentle curve where the arm bends, a cream cuff, then the hand. The sleeve's root is buried in the body (its end is not
    outlined), so it comes out of the shoulder instead of being stuck on. Returns the wrist and the elbow."""
    elbow, wrist = two_link(shoulder, target, l1, l2)
    mid = (shoulder + wrist) * 0.5
    control = mid + (elbow - mid) * 0.8                                              # nearly through the elbow, but softened

    n = 28
    samples = []                                                                     # (centre, normal, half-width) from the root outwards
    _, u0 = _along(shoulder, control, wrist, 0.0)
    root = shoulder - u0 * (width * 0.35)                                            # start a little inside the body
    samples.append((root, QPointF(-u0.y(), u0.x()), width * 0.5))
    for i in range(n):
        t = i / (n - 1)
        pt, u = _along(shoulder, control, wrist, t)
        samples.append((pt, QPointF(-u.y(), u.x()), width * 0.5 * (1.0 - 0.45 * t)))
    left = [c + nm * hw for c, nm, hw in samples]
    right = [c - nm * hw for c, nm, hw in samples]

    body = QPainterPath()
    body.moveTo(left[0])
    for pt in left[1:]: body.lineTo(pt)
    for pt in reversed(right): body.lineTo(pt)
    body.closeSubpath()
    p.setPen(Qt.NoPen); p.setBrush(coat); p.drawPath(body)                           # the sleeve: filled, with no outline round its root

    p.setPen(QPen(OUTLINE, 1.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)); p.setBrush(Qt.NoBrush)
    for edge in (left, right):                                                       # the outline: the two long sides, from the shoulder on
        line = QPainterPath(edge[1])
        for pt in edge[2:]: line.lineTo(pt)
        p.drawPath(line)

    fold = QPainterPath()
    for i in range(int(0.25 * n), int(0.70 * n) + 1):                               # one soft darker fold line along the underside
        c, nm, hw = samples[i + 1]
        pt = c - nm * (0.3 * hw)
        if i == int(0.25 * n): fold.moveTo(pt)
        else: fold.lineTo(pt)
    p.setPen(QPen(coat.darker(120), 1.0)); p.drawPath(fold)

    wrist_pt, u_last = _along(shoulder, control, wrist, 1.0)
    norm_wrist = QPointF(-u_last.y(), u_last.x())
    hw_cuff = width * 0.5 * 0.55 * 1.10
    cuff = QPainterPath()
    for a, b in ((-4.0, 1), (4.0, 1), (4.0, -1), (-4.0, -1)):
        pt = wrist_pt + u_last * a + norm_wrist * (hw_cuff * b)
        cuff.moveTo(pt) if a == -4.0 and b == 1 else cuff.lineTo(pt)
    cuff.closeSubpath()
    p.setPen(QPen(OUTLINE, 1.0)); p.setBrush(CUFF); p.drawPath(cuff)

    draw_hand(p, wrist, math.atan2(u_last.y(), u_last.x()), kind, size=hand_size or max(0.7, width / 18))
    return wrist, elbow
