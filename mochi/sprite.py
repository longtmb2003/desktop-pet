"""Drawing a pet from a sprite pack (see pets/pack.py). One figure image plus interchangeable face overlays, animated with
transforms only (bob, tilt, squash, turn, lie down), so a character needs just a few PNGs.

All drawing is in the definition's own pixel space (`defn.size` square, origin at the feet); the pet widget scales it."""
import math

from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QCursor, QPainter, QPainterPath, QPen, QPolygonF, QRegion

from .limbs import draw_arm, draw_hand
from .renderer import heart, star
from .state import MISCHIEF, SCOLDING, Action, Expression, Motion

INK = QColor(24, 22, 26)


def face_kind(pet):
    """which face overlay the pet wears now"""
    s = pet.state
    if s.expression is Expression.HAPPY: return "laugh"
    if s.expression is Expression.SCARED or s.action in (Action.RANT, Action.YAWN, *SCOLDING): return "talk"
    if s.action in MISCHIEF: return "grin"                                          # naughty: the toothy grin
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


RED = QColor(206, 32, 41)


def shoulder(pk, side, bs, bw, bh):
    """where the arm on art side `side` (-1 left, +1 right) is rooted, in the body's drawing units (origin at the feet)"""
    pt = pk.shoulders.get("left" if side < 0 else "right")
    return QPointF(pt[0] * bs - bw / 2, pt[1] * bs - bh) if pt else QPointF(side * bw * 0.27, -bh * 0.53)


def draw_prop(p, pk, bw, bh, bs, t, mirror):
    """what it holds while working: a red "no entry, busy" sign on a handle, or a laptop. Both hands take hold of it and the arms
    come straight from the shoulders, so it is clearly gripped rather than floating in front of the body"""
    aw = bw * 0.17                                                                    # the sleeve's width at the shoulder
    l1, l2, hsz = bw * 0.32, bw * 0.30, bw * 0.0085
    if pk.work_prop == "sign":
        cy, r = -bh * 0.44, bw * 0.31                                                 # the disc's centre and radius
        grip = QPointF(0, cy + r + 14)                                                # both fists close round the handle, under the sign
        held = [draw_arm(p, pk.coat, shoulder(pk, side, bs, bw, bh), QPointF(side * 7, grip.y()), aw, "grip", l1, l2, hsz)
                for side in (-1, 1)]
        p.save(); p.translate(grip); p.rotate(math.sin(t * 3) * 4); p.translate(-grip)   # the sign sways a little: "not now!"
        p.setPen(QPen(QColor(90, 60, 32), 1.2)); p.setBrush(QColor(150, 104, 58))
        p.drawRoundedRect(QRectF(-3, cy + r - 6, 6, 44), 2, 2)                        # the handle
        p.setPen(QPen(QColor(120, 20, 25), 1.5)); p.setBrush(Qt.white); p.drawEllipse(QPointF(0, cy), r, r)
        p.setPen(QPen(RED, r * 0.24)); p.setBrush(Qt.NoBrush); p.drawEllipse(QPointF(0, cy), r * 0.86, r * 0.86)
        d = r * 0.86 * 0.7071
        p.setPen(QPen(RED, r * 0.24, Qt.SolidLine, Qt.FlatCap)); p.drawLine(QPointF(-d, -d + cy), QPointF(d, d + cy))       # the slash
        p.setPen(QPen(QColor(120, 20, 25), 1)); p.setBrush(RED)
        plaque = QRectF(-bw * 0.24, cy + r - 8, bw * 0.48, 15)                        # "BẬN" across the sign's lower edge
        p.drawRoundedRect(plaque, 3, 3)
        p.save(); p.translate(plaque.center()); p.scale(mirror, 1)                     # text must not come out mirrored
        f = p.font(); f.setBold(True); f.setPixelSize(11); p.setFont(f); p.setPen(Qt.white)
        p.drawText(QRectF(-plaque.width() / 2, -plaque.height() / 2, plaque.width(), plaque.height()), Qt.AlignCenter, "BẬN")
        p.restore()
        p.restore()
        for wrist, elbow in held:                                                     # the arms pass behind the sign: only the fists show
            draw_hand(p, wrist, math.atan2(wrist.y() - elbow.y(), wrist.x() - elbow.x()), "grip", hsz)
    else:
        top = -bh * 0.36
        p.setPen(QPen(QColor(90, 96, 110), 2)); p.setBrush(QColor(176, 184, 198))
        p.drawRoundedRect(QRectF(-bw * 0.28, top, bw * 0.56, bh * 0.16), 4, 4)
        p.setPen(Qt.NoPen); p.setBrush(QColor(236, 240, 246)); p.drawEllipse(QPointF(0, top + bh * 0.08), 3, 3)
        for side in (-1, 1):
            draw_arm(p, pk.coat, shoulder(pk, side, bs, bw, bh), QPointF(side * bw * 0.30, top + bh * 0.08), aw, "grip", l1, l2, hsz)


def riding(pet):
    """is it riding its tricycle now? (a pack with a `ride`, walking or chasing calmly; not staggering, scared, etc.)"""
    pk, s = pet.defn.pack, pet.state
    calm = s.motion is Motion.WALK and s.action in (Action.NONE, Action.CHASE) and s.expression is Expression.NORMAL
    return bool(pk and pk.ride) and calm


def arm_sides(pet, mir):
    """which of the picture's own arms (\"left\" / \"right\", as the art shows them) are replaced by a drawn arm right now"""
    s = pet.state
    if s.action in (Action.WORK, Action.LECTURE): return {"left", "right"}
    if s.action is Action.POINT: screen = 1 if cursor(pet)[0] >= 0 else -1
    elif s.action is Action.WAG: screen = 1
    else: return set()
    return {"right" if (screen if mir >= 0 else -screen) > 0 else "left"}                # (mirrored art has its left on the screen's right)


def body_image(pk, sides):
    """the body picture to draw: the arm-free variant when a drawn arm takes over from the one behind its back"""
    if not sides or not pk.free: return pk.body
    return pk.free["both" if len(sides) == 2 else next(iter(sides))]


def draw_ride(p, ride, t, x, sign):
    """the tricycle rider standing on the feet line, its wheels turning with `x`, how far it has gone (drawing units); `sign` is
    +1 or -1 by whether the picture is drawn mirrored, which flips the sense of rotation"""
    img = ride.image
    rs = ride.height / img.height()
    rect = QRectF(-img.width() * rs / 2, -ride.height, img.width() * rs, ride.height)
    p.drawImage(rect, img)
    p.save(); p.translate(rect.topLeft()); p.scale(rs, rs)                                     # the picture's own pixels from here
    for w in ride.wheels:
        rim = QPainterPath(); rim.addEllipse(QPointF(w["rim_x"], w["rim_y"]), w["rim_rx"], w["rim_ry"])
        if w["avoid"]:
            over = QPainterPath(); over.addPolygon(QPolygonF([QPointF(*a) for a in w["avoid"]])); over.closeSubpath()
            rim = rim.subtracted(over)                                                          # (leave the rider's shoe alone)
        p.save(); p.setClipPath(rim); p.translate(*w["hub"]); p.scale(1.0, w["rim_ry"] / w["rim_rx"])
        turn = math.degrees(x / (w["ry"] * rs)) * sign
        p.setPen(QPen(QColor(150, 82, 32), 4, Qt.SolidLine, Qt.RoundCap))
        for k in range(3):
            p.save(); p.rotate(turn + k * 120); p.drawLine(QPointF(w["rim_rx"] * 0.3, 0), QPointF(w["rim_rx"] * 1.3, 0)); p.restore()
        p.restore()
    p.restore()


def draw_ride_effects(p, pet, bw, bh, t):
    """dust puffs behind the wheels and speed lines: it is in a hurry"""
    back = -pet.facing
    if pet.turning(): return
    p.setPen(Qt.NoPen)
    for i in range(4):
        ph = (t * 2.4 + i / 4) % 1
        p.setBrush(QColor(236, 232, 224, int((1 - ph) * 140)))
        p.drawEllipse(QPointF(back * (bw * 0.42 + ph * 38), -6 - ph * 16), 3 + ph * 7, 3 + ph * 6)
    for i in range(3):
        y, ln = -bh * 0.30 - i * 15, 22 + 8 * math.sin(t * 18 + i * 2)
        p.setPen(QPen(QColor(120, 120, 130, 150 - i * 30), 2, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(back * bw * 0.62, y), QPointF(back * (bw * 0.62 + ln), y))


def cursor(pet):
    """where the mouse pointer is, in the pet's drawing units with the origin at its feet (so it can point at you)"""
    c = QCursor.pos() - pet.pos()
    return c.x() / pet.scale - pet.defn.size / 2, c.y() / pet.scale - pet.defn.feet


def draw_scold(p, pk, bw, bh, bs, t, action, pet, mir):
    """the arm(s) of a scolding character, drawn in the body's own space (so they move, lean and turn with it, and stay rooted at the
    shoulders): jabbing at the pointer, wagging a raised finger, or gesturing left and right with open hands"""
    aw, l1, hsz = bw * 0.26, bw * 0.32, bw * 0.0085
    l2 = bw * 0.30
    full = l1 + l2 - 1                                                                # the arm stretched out straight
    if action is Action.POINT:
        side = 1 if (cursor(pet)[0] >= 0) == (mir >= 0) else -1                       # the art's arm on the pointer's side
        sh = shoulder(pk, side, bs, bw, bh)
        inv, _ = p.worldTransform().inverted()
        c = QCursor.pos() - pet.pos()
        target = inv.map(QPointF(c.x(), c.y()))                                       # the pointer, in the body's own space
        ang = math.atan2(target.y() - sh.y(), target.x() - sh.x())
        jab = full - 2 + 3 * math.sin(t * 12)
        draw_arm(p, pk.coat, sh, sh + QPointF(math.cos(ang), math.sin(ang)) * jab, aw, "point", l1, l2, hsz)
    elif action is Action.WAG:
        side = 1 if mir >= 0 else -1                                                  # the arm on the screen's right
        sh = shoulder(pk, side, bs, bw, bh)
        a = math.radians(-62 + 18 * math.sin(t * 9))                                  # forearm up and out, wagging: "no, no, no"
        elbow = sh + QPointF(side * l1 * 0.95, l1 * 0.25)
        tip = elbow + QPointF(side * math.cos(a), math.sin(a)) * l2
        draw_arm(p, pk.coat, sh, tip, aw, "point", l1, l2, hsz)
    else:
        for side, phase in ((1, 0.0), (-1, math.pi)):                                 # both arms, alternately flung out
            a = math.radians(-20 + 25 * math.sin(t * 6 + phase))
            sh = shoulder(pk, side, bs, bw, bh)
            draw_arm(p, pk.coat, sh, sh + QPointF(side * math.cos(a), math.sin(a)) * full * 0.85, aw, "open", l1, l2, hsz)


def pose(pet):
    """(dx, dy, rot, sx, sy, spin, lying): where the body is and how it is turned, from what the pet is doing"""
    t, s, pk = pet.t, pet.state, pet.defn.pack
    dx = dy = rot = spin = 0.0
    sy = 1 + 0.02 * math.sin(t * 2.4)
    lying = s.motion is Motion.SLEEP
    if riding(pet):
        fast = 1.6 if s.action is Action.CHASE else 1.0
        dy, rot = abs(math.sin(t * 11 * fast)) * 1.8, 3 * pet.facing + math.sin(t * 5) * 1.5      # bouncing along, leaning forward
        if pet.turning():                                                                   # skidding round: leaning hard the wrong way
            rot -= 14 * math.sin(math.pi * (t - pet.turn_start) / pet.defn.turn_s) * pet.facing
    elif s.motion is Motion.WALK and s.action is Action.NONE:
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
    on_wheels = riding(pet)
    if on_wheels:
        draw_ride(p, pk.ride, t, pet.px / pet.scale, 1 if mir >= 0 else -1)
    else:
        rect = QRectF(-bw / 2, -bh, bw, bh)
        img = body_image(pk, arm_sides(pet, mir))
        p.drawImage(rect, img)
        if s.action is Action.WORK: draw_prop(p, pk, bw, bh, bs, t, 1 if mir >= 0 else -1)
        if s.action in SCOLDING: draw_scold(p, pk, bw, bh, bs, t, s.action, pet, mir)
        if pk.head_bottom and (s.action in SCOLDING or s.action is Action.WORK):          # the sleeves pass behind the head, not over it
            p.drawImage(QRectF(rect.x(), rect.y(), bw, pk.head_bottom * bs), img, QRectF(0, 0, img.width(), pk.head_bottom))
        p.save(); p.translate(rect.topLeft()); p.scale(bs, bs)                            # body pixels from here
        bx, by, fw, fh = pk.box
        if lying or s.expression is Expression.DIZZY:
            vector_face(p, s, "sleep" if lying else "dizzy", pk.box)
        else:
            kind = face_kind(pet)
            p.drawImage(QRectF(bx, by, fw, fh), pk.face(kind, t))
        p.restore()
    p.resetTransform(); p.scale(pet.scale, pet.scale); p.translate(d.size / 2, d.feet)    # extras: upright, not turned with the body
    if on_wheels: draw_ride_effects(p, pet, bw, bh, t)
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
        reach = max(reach, bw * 0.9 + 30)                                     # ... or an arm stretched out to point at you
        region = QRegion(QRectF((c - reach) * k, (d.feet - up) * k, 2 * reach * k, (up + down) * k).toRect())
    for x, y, _ in pet.hearts: region += QRegion(QRect(round((c + x - 10) * k), round((d.feet + y - 10) * k), round(20 * k), round(20 * k)))
    return region.intersected(QRegion(0, 0, pet.size, pet.size))
