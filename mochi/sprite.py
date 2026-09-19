"""Drawing a pet from a sprite pack (see pets/pack.py). One figure image plus interchangeable face overlays, animated with
transforms only (bob, tilt, squash, turn, lie down), so a character needs just a few PNGs.

All drawing is in the definition's own pixel space (`defn.size` square, origin at the feet); the pet widget scales it."""
import math

from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QCursor, QPainter, QPainterPath, QPen, QRegion

from .renderer import heart, star
from .state import SCOLDING, Action, Expression, Motion

INK = QColor(24, 22, 26)


def face_kind(pet):
    """which face overlay the pet wears now"""
    s = pet.state
    if s.expression is Expression.HAPPY: return "laugh"
    if s.expression is Expression.SCARED or s.action in (Action.RANT, Action.YAWN, *SCOLDING): return "talk"
    if s.action in (Action.STOMP, Action.DANCE): return "laugh"
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


SKIN = QColor(247, 203, 160)
RED = QColor(206, 32, 41)


def arm(p, pk, sx, hand, bw, bh):
    """a sleeve from the shoulder at x = sx (body units, origin at the feet) to a hand: thick round stroke in the coat's colour"""
    p.setPen(QPen(pk.coat, max(9.0, bw * 0.13), Qt.SolidLine, Qt.RoundCap)); p.drawLine(QPointF(sx, -bh * 0.5), hand)


def hand(p, at):
    p.setPen(QPen(QColor(150, 105, 80), 1)); p.setBrush(SKIN); p.drawEllipse(at, 6.5, 6)


def draw_prop(p, pk, bw, bh, t, mirror):
    """what it holds while working: a red "no entry, busy" sign, or a laptop; both held by two hands with sleeves from the shoulders,
    so it is clearly gripped rather than floating in front of the body"""
    sx = bw * 0.27                                                                    # where the sleeves start: on the chest
    if pk.work_prop == "sign":
        cy, r = -bh * 0.44, bw * 0.30                                                 # the disc's centre and radius
        grip = QPointF(0, cy + 6)                                                     # the sign is held by its sides
        holds = [QPointF(side * (r + 1), cy + 6) for side in (-1, 1)]
        for side, h in zip((-1, 1), holds, strict=True): arm(p, pk, side * sx, h, bw, bh)
        p.save(); p.translate(grip); p.rotate(math.sin(t * 3) * 4); p.translate(-grip)   # the sign sways a little: "not now!"
        p.setPen(QPen(QColor(120, 20, 25), 1.5)); p.setBrush(Qt.white); p.drawEllipse(QPointF(0, cy), r, r)
        p.setPen(QPen(RED, r * 0.24)); p.setBrush(Qt.NoBrush); p.drawEllipse(QPointF(0, cy), r * 0.86, r * 0.86)
        d = r * 0.86 * 0.7071
        p.setPen(QPen(RED, r * 0.24, Qt.SolidLine, Qt.FlatCap)); p.drawLine(QPointF(-d, -d + cy), QPointF(d, d + cy))       # the slash
        p.setPen(QPen(QColor(120, 20, 25), 1)); p.setBrush(RED)
        plaque = QRectF(-bw * 0.24, cy + r + 3, bw * 0.48, 15)
        p.drawRoundedRect(plaque, 3, 3)
        p.save(); p.translate(plaque.center()); p.scale(mirror, 1)                     # text must not come out mirrored
        f = p.font(); f.setBold(True); f.setPixelSize(11); p.setFont(f); p.setPen(Qt.white)
        p.drawText(QRectF(-plaque.width() / 2, -plaque.height() / 2, plaque.width(), plaque.height()), Qt.AlignCenter, "BẬN")
        p.restore()
        p.restore()
        for h in holds: hand(p, h)
    else:
        top = -bh * 0.36
        for side in (-1, 1): arm(p, pk, side * sx, QPointF(side * bw * 0.20, top + 4), bw, bh)
        p.setPen(QPen(QColor(90, 96, 110), 2)); p.setBrush(QColor(176, 184, 198))
        p.drawRoundedRect(QRectF(-bw * 0.28, top, bw * 0.56, bh * 0.16), 4, 4)
        p.setPen(Qt.NoPen); p.setBrush(QColor(236, 240, 246)); p.drawEllipse(QPointF(0, top + bh * 0.08), 3, 3)
        for side in (-1, 1): hand(p, QPointF(side * bw * 0.20, top + 2))              # resting on the top edge


def cursor(pet):
    """where the mouse pointer is, in the pet's drawing units with the origin at its feet (so it can point at you)"""
    c = QCursor.pos() - pet.pos()
    return c.x() / pet.scale - pet.defn.size / 2, c.y() / pet.scale - pet.defn.feet


def finger(p, pk, shoulder, ang, reach, bw):
    """a sleeved arm from `shoulder` out at angle `ang` (radians, screen: y down), ending in a fist with the index finger out"""
    d = QPointF(math.cos(ang), math.sin(ang))
    hand = shoulder + d * reach
    p.setPen(QPen(pk.coat, max(9.0, bw * 0.13), Qt.SolidLine, Qt.RoundCap)); p.drawLine(shoulder, hand)
    p.setPen(QPen(SKIN, 5, Qt.SolidLine, Qt.RoundCap)); p.drawLine(hand, hand + d * 15)              # the pointing finger
    p.setPen(QPen(QColor(150, 105, 80), 1)); p.setBrush(SKIN); p.drawEllipse(hand, 7, 6.5)


def draw_scold(p, pk, bw, bh, t, action, pet, dx, dy):
    """the arm(s) of a scolding character, drawn upright (after the body's own transform): jabbing at the pointer, wagging a raised
    finger, or gesturing left and right"""
    sx, sy0, reach = bw * 0.27, -bh * 0.5 - dy, bw * 0.62
    if action is Action.POINT:
        cx, cy = cursor(pet)
        side = 1 if cx >= 0 else -1
        sh = QPointF(side * sx + dx, sy0)
        finger(p, pk, sh, math.atan2(cy - sh.y(), cx - sh.x()), reach + 5 * math.sin(t * 12), bw)      # the jab
    elif action is Action.WAG:
        sh = QPointF(sx + dx, sy0)
        finger(p, pk, sh, math.radians(-72 + 24 * math.sin(t * 9)), reach * 0.8, bw)                   # up, and side to side: "no, no, no"
    else:
        side = -1 if int(t * 1.6) % 2 else 1
        a = math.radians(-25 + 12 * math.sin(t * 12))
        finger(p, pk, QPointF(side * sx + dx, sy0), math.atan2(math.sin(a), side * math.cos(a)), reach, bw)


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
    elif s.action is Action.POINT: rot, dy = 5 * (1 if cursor(pet)[0] >= 0 else -1), abs(math.sin(t * 12)) * 1.5
    elif s.action is Action.LECTURE: dy, rot = abs(math.sin(t * 6)) * pk.bob * 0.6, math.sin(t * 3) * 4
    elif s.action is Action.STOMP: dy, sy = abs(math.sin(t * 10)) * pk.bob * 1.8, 1 - 0.1 * max(0, math.cos(t * 10))
    elif s.action is Action.PEEK: rot = 24 * pet.facing
    elif s.action is Action.DANGLE: rot, sy = math.sin(t * 4) * 5, 0.96
    elif s.action is Action.DANCE: rot, dy = math.sin(t * 8) * 12, abs(math.sin(t * 8)) * pk.bob * 1.2
    if s.motion is Motion.DRAG: sy, rot = 1.04, math.sin(t * 6) * 3
    if s.expression is Expression.HAPPY and s.motion is not Motion.DRAG: dy = abs(math.sin(t * 10)) * pk.bob
    if s.expression is Expression.DIZZY and s.motion is not Motion.WALK: rot = math.sin(t * 4) * 9
    tired = pet.hot or s.expression is Expression.TIRED
    if s.expression is Expression.SCARED: dx = math.sin(t * 45) * 1.5
    if tired and s.expression in (Expression.NORMAL, Expression.TIRED) and not lying: rot, sy = rot + 3 * pet.facing, sy - 0.02
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
    mir = pet.turn_scale() * pk.art                                                        # -1 draws the art mirrored, 0 is edge-on
    p.rotate(rot); p.scale(sx * mir, sy)
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
    if s.action is Action.WORK: draw_prop(p, pk, bw, bh, t, 1 if mir >= 0 else -1)
    p.resetTransform(); p.scale(pet.scale, pet.scale); p.translate(d.size / 2, d.feet)    # extras: upright, not turned with the body
    if s.action in SCOLDING: draw_scold(p, pk, bw, bh, t, s.action, pet, dx, dy)
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
    tired = (pet.hot or s.expression is Expression.TIRED) and s.expression in (Expression.NORMAL, Expression.TIRED) and not lying
    if s.expression is Expression.SCARED or tired:
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
    return still and s.expression is Expression.NORMAL and not pet.hot and not pet.hearts and pet.squash < 0.03 and not pet.turning()


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
        key = (round(k, 3), pet.facing * pk.art)
        if key not in pk.masks:
            img = pk.body.scaled(max(1, round(bw * k)), max(1, round(bh * k)), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            if pet.facing * pk.art < 0:                                  # (`flipped` needs Qt 6.9; older PySide6 has `mirrored`)
                img = img.flipped(Qt.Horizontal) if hasattr(img, "flipped") else img.mirrored(True, False)
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
        r = math.hypot(bw, bh) / 2 + 8                                    # its corners sweep this circle about the middle
        region = QRegion(QRectF((c - r) * k, (d.feet - bh / 2 - r) * k, 2 * r * k, 2 * r * k).toRect(), QRegion.Ellipse)
    else:
        th = math.radians(max(26, pk.sway + 3))                               # the widest lean: its own waddle, a push, a peek
        hx = bw / 2                                                           # a body leaning about its feet sweeps this box
        sin, cos = math.sin(th), math.cos(th)
        reach, up, down = hx * cos + bh * sin + 12, bh * cos + hx * sin + pk.bob + 40, hx * sin + 8
        reach = max(reach, bw * (0.27 + 0.62) + 5 + 15 + 8)                   # ... or an arm stretched out to point at you
        region = QRegion(QRectF((c - reach) * k, (d.feet - up) * k, 2 * reach * k, (up + down) * k).toRect())
    for x, y, _ in pet.hearts: region += QRegion(QRect(round((c + x - 10) * k), round((d.feet + y - 10) * k), round(20 * k), round(20 * k)))
    return region.intersected(QRegion(0, 0, pet.size, pet.size))
