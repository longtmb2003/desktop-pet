"""Drawing: themes, the pet's vector body and its click-through silhouette. Pure functions of the pet's state."""
import math

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QCursor, QLinearGradient, QPainter, QPainterPath, QPen, QRegion

from .physics import FEET, S
from .state import Action, Expression, Motion

THEMES = {  # body gradient top/bottom, ear, tail, inner ear, eye
    "Kem":     dict(top="#fff4ea", bottom="#ffdcc8", ear="#f7cdb7", tail="#f6c3aa", inner="#ffb3c1", eye="#3b2a35"),
    "Cam":     dict(top="#ffcf9e", bottom="#f5a25d", ear="#f0a466", tail="#ee9a55", inner="#ffb3c1", eye="#3b2a35"),
    "Xám":     dict(top="#e6e8ee", bottom="#c3c7d2", ear="#b9bdc9", tail="#b0b4c1", inner="#ffc2cf", eye="#3b2a35"),
    "Bạc hà":  dict(top="#e3f8ec", bottom="#b9e8cf", ear="#a6dcc0", tail="#9dd6b8", inner="#ffb3c1", eye="#3b2a35"),
    "Hồng":    dict(top="#ffe8f0", bottom="#ffc2d6", ear="#ffb0c9", tail="#ffa6c1", inner="#ff8fb0", eye="#3b2a35"),
}


def heart(s):
    p = QPainterPath(); p.moveTo(0, s * .9)
    p.cubicTo(-s * 1.6, -s * .2, -s * .6, -s * 1.3, 0, -s * .4)
    p.cubicTo(s * .6, -s * 1.3, s * 1.6, -s * .2, 0, s * .9)
    return p


def star(r):
    p = QPainterPath()
    for i in range(10):
        a, rr = -math.pi / 2 + i * math.pi / 5, r if i % 2 == 0 else r * .45
        p.lineTo(rr * math.cos(a), rr * math.sin(a)) if i else p.moveTo(rr * math.cos(a), rr * math.sin(a))
    p.closeSubpath()
    return p


def silhouette(f, sleep, stretch, hearts, flip=False):
    """Region of the pet window that should catch clicks; the rest is click-through. f = -facing."""
    c = S // 2
    if flip: return QRegion(c - 110, FEET - 62 - 110, 220, 220, QRegion.Ellipse)    # a turning pet sweeps a circle around its middle
    r = QRegion(c - 72, FEET - 88, 144, 100, QRegion.Ellipse)                   # body
    r += QRegion(c - 66, FEET - 106, 132, 60)                                  # ears
    r += QRegion(c - 60, FEET - 14, 120, 28)                                    # feet + shadow
    r += QRegion(min(c + f * 30, c + f * 100), FEET - 92, 70, 96)               # tail
    if sleep: r += QRegion(c + 28, FEET - 124, 48, 44)                         # zzz
    if stretch: r += r.translated(-f * 10, 0) + r.translated(0, -8)            # the pose leans forward and lifts its bum
    for x, y, _ in hearts: r += QRegion(int(c + x - 10), int(FEET + y - 10), 20, 20)
    return r


def paint(pet, p):
    """Draw `pet` onto QPainter `p` (a painter on the pet window)."""
    p.setRenderHint(QPainter.Antialiasing)
    p.translate(S / 2, FEET)
    t, state = pet.t, pet.state
    motion, act = state.motion, state.action
    happy, sleep, drag = state.expression is Expression.HAPPY, motion is Motion.SLEEP, motion is Motion.DRAG
    dizzy = state.expression is Expression.DIZZY
    walking = motion is Motion.WALK and act is Action.NONE          # a chase runs, it doesn't use the walk cycle
    up = motion in (Motion.AIRBORNE, Motion.DRAG)
    th = THEMES[pet.theme]
    DARK, TAIL, EAR, PINK = (QColor(th[k]) for k in ("eye", "tail", "ear", "inner"))
    if pet.grounded:                                                          # shadow only when standing
        p.setPen(Qt.NoPen); p.setBrush(QColor(0, 0, 0, 38)); p.drawEllipse(QPointF(0, 1), 46, 6)

    hop, sy = 0.0, 1 + 0.025 * math.sin(t * 2.4)
    if walking: hop = abs(math.sin(t * 9)) * 7
    elif sleep: sy = 1 + 0.04 * math.sin(t * 1.2)
    elif drag: sy = 1.08
    o = math.sin(math.pi * min(1, (t - pet.began) / pet.dur))               # 0 -> 1 -> 0 over a one-shot move
    tilt = shift = 0.0
    if act is Action.STRETCH: sy -= .14 * o; tilt = 4 * o; shift = 8 * o                           # stretch forward, bum up
    elif act is Action.YAWN: sy += .05 * o; tilt = -5 * o
    elif act is Action.CHASE: hop = abs(math.sin(t * 14)) * 9
    sy -= pet.squash
    sx = 2 - sy if not drag else .94        # keep volume: taller = thinner
    p.translate(shift * pet.facing, -hop)
    if act is Action.FLIP:                                                                         # one full turn about the body's middle
        p.translate(0, -62); p.rotate(360 * min(1, (t - pet.began) / pet.dur) * pet.facing); p.translate(0, 62)
    p.rotate(tilt * pet.facing)
    p.scale(-sx * pet.facing, sy)                               # tail trails behind the walking direction

    def blob(c, x, y, rx, ry):
        p.setPen(Qt.NoPen); p.setBrush(c); p.drawEllipse(QPointF(x, y), rx, ry)

    # tail
    wag = math.sin(t * (9 if happy else 4)) * (2 if sleep else 9)
    tail = QPainterPath(QPointF(38, -22))
    tail.cubicTo(70, -25, 72, -58 + wag, 58, -70 + wag)
    p.setPen(QPen(TAIL, 13, Qt.SolidLine, Qt.RoundCap)); p.setBrush(Qt.NoBrush); p.drawPath(tail)

    # ears (right one is the left one mirrored)
    for m in (1, -1):
        p.save(); p.scale(m, 1)
        for col, k in ((EAR, 1), (PINK, .55)):
            ear = QPainterPath(QPointF(-44 * k - 2, -52)); ear.lineTo(-38 * k - 2, -94 + 8 * (1 - k)); ear.lineTo(-14 * k - 6, -74)
            ear.closeSubpath()
            p.setPen(QPen(col, 8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)); p.setBrush(col)
            if k < 1: p.translate(-1, 3)
            p.drawPath(ear)
        p.restore()

    # feet
    for i, m in enumerate((-1, 1)):
        if up: blob(TAIL, m * 18, 6 + math.sin(t * 8 + i * 2) * 3, 9, 10)
        else:  blob(TAIL, m * 20, -5 - (max(0, math.sin(t * 9 + i * math.pi)) * 5 if walking else 0), 13, 8)

    # body
    g = QLinearGradient(0, -80, 0, -4)
    g.setColorAt(0, QColor(th["top"])); g.setColorAt(1, QColor(th["bottom"]))
    p.setPen(Qt.NoPen); p.setBrush(QBrush(g)); p.drawEllipse(QRectF(-47, -80, 94, 76))

    # face
    for m in (-1, 1): blob(QColor(255, 157, 176, 120), m * 31, -37, 8, 4.5)
    cur = QCursor.pos() - pet.pos() - QPoint(S // 2, FEET - 46)                 # eyes follow the cursor
    lx, ly = max(-1, min(1, cur.x() / 250)) * -2.5 * pet.facing, max(-1, min(1, cur.y() / 250)) * 1.5
    pen = QPen(DARK, 3, Qt.SolidLine, Qt.RoundCap)
    for x in (-19, 19):
        if dizzy:                                                          # X eyes
            arc = QPainterPath(QPointF(x - 6, -52)); arc.lineTo(x + 6, -40); arc.moveTo(x + 6, -52); arc.lineTo(x - 6, -40)
        elif sleep or act in (Action.YAWN, Action.STRETCH, Action.GROOM) or pet.blink > 0:
            arc = QPainterPath(QPointF(x - 7, -46)); arc.quadTo(x, -40, x + 7, -46)
        elif happy:
            arc = QPainterPath(QPointF(x - 7, -43)); arc.quadTo(x, -53, x + 7, -43)
        else:
            r = 1.2 if drag else 1
            blob(DARK, x + lx, -46 + ly, 7.5 * r, 9.5 * r)
            blob(Qt.white, x + lx * 1.6 - 2.5, -49 + ly, 3, 3); blob(Qt.white, x + lx + 3, -42 + ly, 1.5, 1.5)
            continue
        p.setPen(pen); p.setBrush(Qt.NoBrush); p.drawPath(arc)
    if drag: blob(DARK, 0, -35, 3, 4)
    elif happy: blob(PINK.darker(130), 0, -35, 4, 4.5)
    elif dizzy: blob(PINK.darker(150), 0, -34, 3.5, 3)
    elif act is Action.YAWN: blob(PINK.darker(150), 0, -33, 4 + 3 * o, 2 + 8 * o)
    else:
        mouth = QPainterPath(QPointF(-5, -38)); mouth.quadTo(-2.5, -33, 0, -38); mouth.quadTo(2.5, -33, 5, -38)
        p.setPen(QPen(DARK, 2, Qt.SolidLine, Qt.RoundCap)); p.setBrush(Qt.NoBrush); p.drawPath(mouth)

    if act is Action.GROOM:                                          # lick a paw, stroke the cheek
        lift = (.5 + .5 * math.sin(t * 9)) * min(1, o * 3)
        blob(TAIL, 27 - 5 * lift, -16 - 22 * lift, 8, 10)
        blob(PINK, 25 - 5 * lift, -24 - 22 * lift, 2.5, 2)

    # floating extras, drawn in unscaled space
    p.resetTransform(); p.translate(S / 2, FEET)
    if sleep:
        f = p.font(); f.setBold(True)
        for i in range(3):
            ph = (t * .5 + i / 3) % 1
            f.setPointSizeF(9 + ph * 7); p.setFont(f)
            p.setPen(QColor(122, 134, 201, int(math.sin(ph * math.pi) * 230)))
            p.drawText(QPointF(34 + ph * 22, -84 - ph * 30), "z")
    if dizzy:                                                          # stars circling the head
        p.setPen(Qt.NoPen); p.setBrush(QColor("#ffcf5a"))
        for i in range(3):
            a = t * 5 + i * 2.094
            p.save(); p.translate(34 * math.cos(a), -104 + 9 * math.sin(a)); p.rotate(t * 90); p.drawPath(star(5)); p.restore()
    for x, y, life in pet.hearts:
        p.setPen(Qt.NoPen); p.setBrush(QColor(255, 111, 145, int(min(1, life) * 230)))
        p.save(); p.translate(x, y); p.drawPath(heart(5 + 3 * math.sin(life * 6))); p.restore()
