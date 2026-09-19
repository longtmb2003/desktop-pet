"""Drawing a pet from a sprite pack (see pets/pack.py). One figure image plus interchangeable face overlays, animated with
transforms only (bob, tilt, squash, turn, lie down), so a character needs just a few PNGs.

All drawing is in the definition's own pixel space (`defn.size` square, origin at the feet); the pet widget scales it."""
import math

from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QRegion

from .renderer import heart, star
from .state import Action, Expression, Motion

INK = QColor(24, 22, 26)


def face_kind(pet):
    """which face overlay the pet wears now"""
    s = pet.state
    if s.expression is Expression.HAPPY: return "laugh"
    if s.expression is Expression.SCARED or s.action in (Action.RANT, Action.YAWN): return "talk"
    if pet.bubble.isVisible() and s.motion is not Motion.SLEEP: return "talk"       # moves its mouth while its words are up
    return "neutral"


def vector_face(p, s, kind, box):
    """faces drawn in ink strokes where the pack has no image: "sleep" (closed eyes) and "dizzy" (crossed eyes), in body pixels"""
    x, y, w, h = box
    p.setPen(QPen(INK, max(2.0, w * 0.045), Qt.SolidLine, Qt.RoundCap)); p.setBrush(Qt.NoBrush)
    for cx in (x + w * 0.30, x + w * 0.70):
        cy, r = y + h * 0.36, w * 0.10
        path = QPainterPath()
        if kind == "sleep":
            path.moveTo(cx - r, cy); path.quadTo(cx, cy + r, cx + r, cy)
        else:
            path.moveTo(cx - r, cy - r); path.lineTo(cx + r, cy + r); path.moveTo(cx + r, cy - r); path.lineTo(cx - r, cy + r)
        p.drawPath(path)
    p.setPen(Qt.NoPen); p.setBrush(INK)
    p.drawEllipse(QPointF(x + w * 0.5, y + h * 0.72), w * 0.05, w * (0.04 if kind == "sleep" else 0.06))


def pose(pet):
    """(dx, dy, rot, sx, sy, spin, lying): where the body is and how it is turned, from what the pet is doing"""
    t, s, pk = pet.t, pet.state, pet.defn.pack
    dx = dy = rot = spin = 0.0
    sy = 1 + 0.02 * math.sin(t * 2.4)
    lying = s.motion is Motion.SLEEP
    if s.motion is Motion.WALK and s.action is Action.NONE:
        dy, rot = abs(math.sin(t * 9)) * pk.bob, math.sin(t * 9) * pk.sway                # a waddle
        if s.expression is Expression.DIZZY: rot = math.sin(t * 4) * 9
    elif s.action is Action.CHASE:
        dy, rot = abs(math.sin(t * 14)) * pk.bob * 1.4, 7 * pet.facing
    elif s.action is Action.PUSH:
        rot = (10 + 2 * math.sin(t * 14)) * pet.facing
    elif s.action is Action.STRETCH:
        sy += 0.05
    if s.motion is Motion.DRAG: sy, rot = 1.04, math.sin(t * 6) * 3
    if s.expression is Expression.HAPPY and s.motion is not Motion.DRAG: dy = abs(math.sin(t * 10)) * pk.bob
    if s.expression is Expression.DIZZY and s.motion is not Motion.WALK: rot = math.sin(t * 4) * 9
    if s.expression is Expression.SCARED: dx = math.sin(t * 45) * 1.5
    if pet.hot and s.expression is Expression.NORMAL and not lying: rot, sy = rot + 3 * pet.facing, sy - 0.02
    if s.action is Action.FLIP: spin = 360 * min(1, (t - pet.began) / pet.dur) * pet.facing
    sy -= pet.squash
    return dx, dy, rot, 2 - sy, sy, spin, lying


def paint_sprite(pet, p):
    p.setRenderHint(QPainter.Antialiasing); p.setRenderHint(QPainter.SmoothPixmapTransform)
    d, pk, s, t = pet.defn, pet.defn.pack, pet.state, pet.t
    p.translate(d.size / 2, d.feet)                                                       # origin: the feet
    bs = d.height / pk.body.height()
    bw, bh = pk.body.width() * bs, d.height
    if pet.grounded and s.action is not Action.FLIP:                              # shadow
        p.setPen(Qt.NoPen); p.setBrush(QColor(0, 0, 0, 38)); p.drawEllipse(QPointF(0, 1), bw * 0.42, 6)
    dx, dy, rot, sx, sy, spin, lying = pose(pet)
    p.translate(dx, -dy)
    if lying:                                                                             # asleep: flat on the floor
        p.translate(0, -bw / 2); p.rotate(90 * pet.facing); p.translate(0, bh / 2)
    elif spin:
        p.translate(0, -bh / 2); p.rotate(spin); p.translate(0, bh / 2)
    p.rotate(rot); p.scale(sx * pet.facing, sy)
    rect = QRectF(-bw / 2, -bh, bw, bh)
    p.drawImage(rect, pk.body)
    p.save(); p.translate(rect.topLeft()); p.scale(bs, bs)                                # body pixels from here
    bx, by, fw, fh = pk.box
    if lying or s.expression is Expression.DIZZY:
        vector_face(p, s, "sleep" if lying else "dizzy", pk.box)
    else:
        kind = face_kind(pet)
        p.drawImage(QRectF(bx, by, fw, fh), pk.face(kind, t))
    p.restore()
    if s.action is Action.WORK:                                                           # the back of a tiny laptop at waist height
        p.setPen(QPen(QColor(90, 96, 110), 2)); p.setBrush(QColor(176, 184, 198))
        p.drawRoundedRect(QRectF(-bw * 0.28, -bh * 0.36, bw * 0.56, bh * 0.16), 4, 4)
        p.setPen(Qt.NoPen); p.setBrush(QColor(236, 240, 246)); p.drawEllipse(QPointF(0, -bh * 0.28), 3, 3)
    p.resetTransform(); p.scale(pet.scale, pet.scale); p.translate(d.size / 2, d.feet)    # extras: upright, not turned with the body
    if lying:
        f = p.font(); f.setBold(True)
        for i in range(3):
            ph = (t * .5 + i / 3) % 1
            f.setPointSizeF(9 + ph * 7); p.setFont(f)
            p.setPen(QColor(122, 134, 201, int(math.sin(ph * math.pi) * 230)))
            p.drawText(QPointF(bh * 0.30 + ph * 22, -bw - 6 - ph * 30), "z")
    if s.expression is Expression.DIZZY:
        p.setPen(Qt.NoPen); p.setBrush(QColor("#ffcf5a"))
        for i in range(3):
            a = t * 5 + i * 2.094
            p.save(); p.translate(bw * 0.4 * math.cos(a), -bh - 4 + 9 * math.sin(a)); p.rotate(t * 90); p.drawPath(star(6)); p.restore()
    if s.expression is Expression.SCARED or (pet.hot and s.expression is Expression.NORMAL and not lying):
        for i, sx_ in enumerate((-bw * 0.42, bw * 0.42) if s.expression is not Expression.SCARED else (bw * 0.42,)):
            ph = (t * 0.7 + i * 0.5) % 1
            p.setPen(Qt.NoPen); p.setBrush(QColor(110, 185, 255, int(math.sin(ph * math.pi) * 230)))
            p.drawEllipse(QPointF(sx_, -bh * 0.8 + ph * 34), 3.5, 5)
    for x, y, life in pet.hearts:
        p.setPen(Qt.NoPen); p.setBrush(QColor(255, 111, 145, int(min(1, life) * 230)))
        p.save(); p.translate(x, y); p.drawPath(heart(5 + 3 * math.sin(life * 6))); p.restore()


def _static(pet):
    s = pet.state
    still = s.motion is Motion.IDLE and s.action in (Action.NONE, Action.RANT, Action.YAWN)
    return still and s.expression is Expression.NORMAL and not pet.hot and not pet.hearts and pet.squash < 0.03


def sprite_mask_key(pet):
    s = pet.state
    kind = "sleep" if s.motion is Motion.SLEEP else "flip" if s.action is Action.FLIP else "alpha" if _static(pet) else "box"
    return (kind, pet.facing if kind == "alpha" else 0, tuple((int(x), int(y)) for x, y, _ in pet.hearts))


def sprite_mask(pet):
    """the clickable region, in window pixels. Standing still: the figure's exact outline. Anything that turns or leans: a box
    around where it can be (it must cover every painted pixel, or the window mask would cut them off)."""
    d, pk, k = pet.defn, pet.defn.pack, pet.scale
    kind = sprite_mask_key(pet)[0]
    bs = d.height / pk.body.height()
    bw, bh, c = pk.body.width() * bs, d.height, d.size / 2
    if kind == "alpha":
        key = (round(k, 3), pet.facing)
        if key not in pk.masks:
            img = pk.body.scaled(max(1, round(bw * k)), max(1, round(bh * k)), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            if pet.facing < 0: img = img.flipped(Qt.Horizontal)
            outline = QRegion()
            for y in range(img.height()):                                # anything faintly visible (the antialiased edge) is clickable
                x = 0
                while x < img.width():
                    if img.pixel(x, y) >> 24 > 16:
                        x0 = x
                        while x < img.width() and img.pixel(x, y) >> 24 > 16: x += 1
                        outline += QRegion(x0, y, x - x0, 1)
                    else: x += 1
            grow, region = max(3, round(0.03 * bh * k)), QRegion()      # breathing swells and shifts the figure: dilate the outline
            for dx in (-grow, 0, grow):
                for dy in (-grow, 0, grow): region += outline.translated(dx, dy)
            pk.masks[key] = region.translated(round((c - bw / 2) * k), round((d.feet - bh) * k))
        region = pk.masks[key]
    elif kind == "sleep":
        rect = QRectF((c - bh / 2 - 6) * k, (d.feet - bw - 66) * k, (bh + 40) * k, (bw + 70) * k)      # lying down, room for the zzz
        region = QRegion(rect.toRect())
    elif kind == "flip":
        r = bh / 2 + 10
        region = QRegion(QRectF((c - r) * k, (d.feet - bh / 2 - r) * k, 2 * r * k, 2 * r * k).toRect(), QRegion.Ellipse)
    else:
        m = bh * math.sin(math.radians(14)) + 12
        region = QRegion(QRectF((c - bw / 2 - m) * k, (d.feet - bh - 40) * k, (bw + 2 * m) * k, (bh + 46) * k).toRect())
    for x, y, _ in pet.hearts: region += QRegion(QRect(round((c + x - 10) * k), round((d.feet + y - 10) * k), round(20 * k), round(20 * k)))
    return region.intersected(QRegion(0, 0, pet.size, pet.size))
