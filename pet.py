#!/usr/bin/env python3
"""Mochi: a tiny vector desktop pet. Left-drag to pick up, click to pet, right-click for menu."""
import os, sys, math, random, json
os.environ.setdefault("QT_QPA_PLATFORM", "xcb")  # Wayland forbids self-positioning; XWayland allows it
from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, QPoint, QObject, Slot, ClassInfo
from PySide6.QtDBus import QDBusConnection, QDBusInterface
from PySide6.QtGui import (QPainter, QColor, QPen, QBrush, QPainterPath, QGuiApplication,
                           QLinearGradient, QCursor, QRegion)
from PySide6.QtWidgets import QApplication, QWidget, QMenu

S, FEET = 160, 146                  # window size, y of the floor line inside the window
DUR = {"idle": (2, 5), "walk": (3, 8), "sleep": (8, 20), "happy": (1.4, 1.4)}  # seconds per state
GRAVITY, WALK_SPEED = 1800, 55
HEAD = 190                          # a window must be this far below the screen top to be stood on
DARK, TAIL, EAR, PINK = QColor("#3b2a35"), QColor("#f6c3aa"), QColor("#f7cdb7"), QColor("#ffb3c1")


def heart(s):
    p = QPainterPath(); p.moveTo(0, s * .9)
    p.cubicTo(-s * 1.6, -s * .2, -s * .6, -s * 1.3, 0, -s * .4)
    p.cubicTo(s * .6, -s * 1.3, s * 1.6, -s * .2, 0, s * .9)
    return p


@ClassInfo({"D-Bus Interface": "org.mochi.Pet"})
class Bus(QObject):
    """Receives window rects pushed by kwin.js (Wayland won't let a normal app list other windows)."""
    def __init__(self, pet):
        super().__init__()
        self.pet = pet

    @Slot(str)
    def windows(self, js):
        self.pet.wins = {i: (x, y, w, h) for i, x, y, w, h in json.loads(js)}


class Pet(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(S, S)
        self.t = self.vy = self.squash = self.blink = 0.0
        self.facing, self.hearts = 1, []            # hearts: [x, y, life]
        self.wins, self.support, self.vx, self.grounded = {}, None, 0.0, False   # wins: id -> (x, y, w, h); support: id of the window we stand on
        self.next_blink, self.moved, self.press, self.mask_key = 2.0, False, None, None
        g = self.screen_geo()
        self.px, self.py = random.uniform(g.left() + 80, g.right() - 240), g.top() - 100
        self.set_state("fall")
        self.timer = QTimer(self, interval=33, timeout=self.tick)
        self.timer.start()
        self.bus = Bus(self)
        sb = QDBusConnection.sessionBus()
        sb.registerService("org.mochi.Pet")
        sb.registerObject("/pet", self.bus, QDBusConnection.ExportAllSlots)
        self.load_kwin_script(sb)

    def load_kwin_script(self, sb):
        # ponytail: KDE only; elsewhere the pet just walks on the screen floor
        kw = QDBusInterface("org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting", sb)
        if not kw.isValid(): return
        kw.call("unloadScript", "mochi")
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kwin.js")
        sid = kw.call("loadScript", path, "mochi").arguments()[0]
        QDBusInterface("org.kde.KWin", f"/Scripting/Script{sid}", "org.kde.kwin.Script", sb).call("run")
        QApplication.instance().aboutToQuit.connect(lambda: kw.call("unloadScript", "mochi"))

    # ---- behaviour -------------------------------------------------------
    def pick_next(self):
        w = {"idle": 4, "walk": 3, "sleep": 1}
        w.pop(self.state, None)   # never repeat the action it just finished
        return random.choices(list(w), list(w.values()))[0]

    def set_state(self, s):
        self.state = s
        lo, hi = DUR.get(s, (0, 0))
        self.until = self.t + random.uniform(lo, hi)
        if s == "walk":
            self.facing = random.choice((-1, 1))

    def screen_geo(self):
        c = QPoint(int(getattr(self, "px", 0)) + S // 2, int(getattr(self, "py", 0)) + FEET)
        return (QGuiApplication.screenAt(c) or QGuiApplication.primaryScreen()).availableGeometry()

    def tick(self):
        dt = 0.033
        self.t += dt
        self.squash *= 0.85
        if self.t > self.next_blink:
            self.blink, self.next_blink = 0.15, self.t + random.uniform(2, 5)
        self.blink -= dt
        self.hearts = [[x, y - 40 * dt, l - dt] for x, y, l in self.hearts if l > dt]
        if self.state != "drag":
            g = self.screen_geo()
            cx = self.px + S / 2
            floor, wid = self.surface(cx, self.py + FEET, g)
            if wid is not None and wid == self.support and self.vy >= 0:
                self.py, self.grounded = floor, True               # riding the window it stands on
            elif self.py < floor - 0.5 or self.vy < 0:             # airborne
                self.grounded = False
                self.vy += GRAVITY * dt
                self.py += self.vy * dt
                self.px = max(g.left() - 40, min(g.right() - S + 40, self.px + self.vx * dt))
                if self.py >= floor:
                    self.py, self.vy, self.vx, self.squash, self.support, self.grounded = floor, 0.0, 0.0, 0.3, wid, True
                    if self.state == "fall":
                        self.set_state("idle")
            else:
                self.support, self.grounded = wid, True
                if self.state == "walk":
                    self.walk(dt, g, cx, wid)
            if self.state in DUR and self.t > self.until:
                self.set_state("idle" if self.state == "happy" else self.pick_next())
            self.move(int(self.px), int(self.py))
        self.update_mask()
        self.update()

    def surface(self, cx, feet, g):
        """(window-y of the surface under the feet, id of the window it is or None for the screen floor)"""
        best, wid = g.bottom() + 1, None
        for i, (x, y, w, h) in self.wins.items():
            if x + 24 <= cx <= x + w - 24 and y >= g.top() + HEAD and y < best and (y >= feet - 6 or i == self.support):
                best, wid = y, i
        return best - FEET, wid

    def walk(self, dt, g, cx, wid):
        step = self.facing * WALK_SPEED * dt
        self.px += step; cx += step
        lo, hi = g.left() + 50, g.right() - 50
        if wid is not None:
            x, _, w, _ = self.wins[wid]
            lo, hi = max(lo, x + 34), min(hi, x + w - 34)
        elif random.random() < 0.004:                              # on the floor: sometimes hop onto a nearby window
            self.hop_to(cx, self.py + FEET, g)
        if cx < lo or cx > hi:
            out = -1 if cx < lo else 1
            if wid is not None and random.random() < 0.4:          # hop off the window edge
                self.facing, self.vx, self.vy, self.support = out, out * 140, -260, None
            else:
                self.facing = -out

    def hop_to(self, cx, feet, g):
        for x, y, w, h in self.wins.values():
            up = feet - y                                          # how high the top is above our feet
            if 20 < up < 200 and y >= g.top() + HEAD and x - 120 < cx < x + w + 120:
                tx = max(x + 40, min(x + w - 40, cx))              # aim for a spot on top, then solve the arc
                vy = -math.sqrt(2 * GRAVITY * (up + 40))
                t = (-vy + math.sqrt(vy * vy - 2 * GRAVITY * up)) / GRAVITY
                self.vy, self.vx = vy, (tx - cx) / t
                if tx != cx: self.facing = 1 if tx > cx else -1
                return

    def update_mask(self):
        # clip the window to the pet's silhouette so clicks pass through the transparent rest
        c, f, sleep = S // 2, self.facing, self.state == "sleep"
        key = (f, sleep, tuple((int(x), int(y)) for x, y, _ in self.hearts))
        if key == self.mask_key: return
        self.mask_key = key
        r = QRegion(c - 64, FEET - 88, 128, 100, QRegion.Ellipse)                   # body
        r += QRegion(c - 58, FEET - 106, 116, 60)                                  # ears
        r += QRegion(c - 60, FEET - 14, 120, 28)                                    # feet + shadow
        r += QRegion(min(c + f * 30, c + f * 100), FEET - 92, 70, 80)               # tail
        if sleep: r += QRegion(c + 28, FEET - 124, 48, 44)                         # zzz
        for x, y, _ in self.hearts: r += QRegion(int(c + x - 10), int(FEET + y - 10), 20, 20)
        self.setMask(r)

    # ---- input -----------------------------------------------------------
    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton: return
        g = e.globalPosition().toPoint()
        self.press, self.moved, self.off = g, False, g - self.pos()

    def mouseMoveEvent(self, e):
        if self.press is None: return
        g = e.globalPosition().toPoint()
        if not self.moved and (g - self.press).manhattanLength() > 4:
            self.moved = True
            self.support, self.vx = None, 0.0
            self.set_state("drag")
        if self.moved:
            p = g - self.off
            self.px, self.py, self.vy = p.x(), p.y(), 0.0
            self.move(p)

    def mouseReleaseEvent(self, e):
        if self.press is None: return
        self.press = None
        if self.moved:
            self.set_state("fall")
        else:                                                # a click = a pet
            self.set_state("happy")
            self.vy = -420
            self.hearts += [[random.uniform(-30, 30), -95, 1.2 + random.random() * .5] for _ in range(4)]

    def contextMenuEvent(self, e):
        m = QMenu(self)
        m.addAction("Ngủ", lambda: self.set_state("sleep"))
        m.addAction("Thoát", QApplication.quit)
        m.exec(e.globalPos())

    # ---- drawing ---------------------------------------------------------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.translate(S / 2, FEET)
        t, st = self.t, self.state
        up = st in ("fall", "drag")
        if self.grounded:                                                          # shadow only when standing
            p.setPen(Qt.NoPen); p.setBrush(QColor(0, 0, 0, 38)); p.drawEllipse(QPointF(0, 1), 46, 6)

        hop, sy = 0.0, 1 + 0.025 * math.sin(t * 2.4)
        if st == "walk": hop = abs(math.sin(t * 9)) * 7
        elif st == "sleep": sy = 1 + 0.04 * math.sin(t * 1.2)
        elif st == "drag": sy = 1.08
        sy -= self.squash
        sx = 2 - sy if st != "drag" else .94        # keep volume: taller = thinner
        p.translate(0, -hop)
        p.scale(sx * self.facing, sy)

        def blob(c, x, y, rx, ry):
            p.setPen(Qt.NoPen); p.setBrush(c); p.drawEllipse(QPointF(x, y), rx, ry)

        # tail
        wag = math.sin(t * (9 if st == "happy" else 4)) * (2 if st == "sleep" else 9)
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
            else:  blob(TAIL, m * 20, -5 - (max(0, math.sin(t * 9 + i * math.pi)) * 5 if st == "walk" else 0), 13, 8)

        # body
        g = QLinearGradient(0, -80, 0, -4)
        g.setColorAt(0, QColor("#fff4ea")); g.setColorAt(1, QColor("#ffdcc8"))
        p.setPen(Qt.NoPen); p.setBrush(QBrush(g)); p.drawEllipse(QRectF(-47, -80, 94, 76))

        # face
        for m in (-1, 1): blob(QColor(255, 157, 176, 120), m * 31, -37, 8, 4.5)
        cur = QCursor.pos() - self.pos() - QPoint(S // 2, FEET - 46)                 # eyes follow the cursor
        lx, ly = max(-1, min(1, cur.x() / 250)) * 2.5 * self.facing, max(-1, min(1, cur.y() / 250)) * 1.5
        pen = QPen(DARK, 3, Qt.SolidLine, Qt.RoundCap)
        for x in (-19, 19):
            if st == "sleep" or self.blink > 0:
                arc = QPainterPath(QPointF(x - 7, -46)); arc.quadTo(x, -40, x + 7, -46)
            elif st == "happy":
                arc = QPainterPath(QPointF(x - 7, -43)); arc.quadTo(x, -53, x + 7, -43)
            else:
                r = 1.2 if st == "drag" else 1
                blob(DARK, x + lx, -46 + ly, 7.5 * r, 9.5 * r)
                blob(Qt.white, x + lx * 1.6 - 2.5, -49 + ly, 3, 3); blob(Qt.white, x + lx + 3, -42 + ly, 1.5, 1.5)
                continue
            p.setPen(pen); p.setBrush(Qt.NoBrush); p.drawPath(arc)
        if st == "drag": blob(DARK, 0, -35, 3, 4)
        elif st == "happy": blob(PINK.darker(130), 0, -35, 4, 4.5)
        else:
            mouth = QPainterPath(QPointF(-5, -38)); mouth.quadTo(-2.5, -33, 0, -38); mouth.quadTo(2.5, -33, 5, -38)
            p.setPen(QPen(DARK, 2, Qt.SolidLine, Qt.RoundCap)); p.setBrush(Qt.NoBrush); p.drawPath(mouth)

        # floating extras, drawn in unscaled space
        p.resetTransform(); p.translate(S / 2, FEET)
        if st == "sleep":
            f = p.font(); f.setBold(True)
            for i in range(3):
                ph = (t * .5 + i / 3) % 1
                f.setPointSizeF(9 + ph * 7); p.setFont(f)
                p.setPen(QColor(122, 134, 201, int(math.sin(ph * math.pi) * 230)))
                p.drawText(QPointF(34 + ph * 22, -84 - ph * 30), "z")
        for x, y, life in self.hearts:
            p.setPen(Qt.NoPen); p.setBrush(QColor(255, 111, 145, int(min(1, life) * 230)))
            p.save(); p.translate(x, y); p.drawPath(heart(5 + 3 * math.sin(life * 6))); p.restore()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    pet = Pet(); pet.show()
    sys.exit(app.exec())
