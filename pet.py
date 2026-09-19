#!/usr/bin/env python3
"""Mochi: a tiny vector desktop pet. Left-drag to pick up, click to pet, right-click for menu."""
import os, sys, math, random, json, signal, logging
if os.environ.get("WAYLAND_DISPLAY"):
    os.environ.setdefault("QT_QPA_PLATFORM", "xcb")  # Wayland forbids self-positioning; XWayland allows it
from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, QPoint, QObject, Slot, ClassInfo, QSettings, QElapsedTimer
from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage
from PySide6.QtGui import (QPainter, QColor, QPen, QBrush, QPainterPath, QGuiApplication,
                           QLinearGradient, QCursor, QRegion)
from PySide6.QtWidgets import QApplication, QWidget, QMenu

log = logging.getLogger("mochi")
S, FEET = 160, 146                  # window size, y of the floor line inside the window
DUR = {"idle": (2, 5), "walk": (3, 8), "sleep": (8, 20), "happy": (1.4, 1.4),      # seconds per state
       "yawn": (1.8, 1.8), "stretch": (2.4, 2.4), "groom": (3, 4.5), "chase": (5, 9)}
GRAVITY, WALK_SPEED = 1800, 55
MAX_DT = 0.05                       # cap one frame's time step so a stall can't launch the pet through a window
HEAD = 190                          # a window must be this far below the screen top to be stood on
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


def parse_windows(js):
    """kwin.js payload '[[id, x, y, w, h], ...]' -> {id: (x, y, w, h)}.
    Malformed entries are skipped; a payload that isn't a list raises ValueError/TypeError (rejected whole)."""
    wins = {}
    for e in json.loads(js):
        try:
            i, x, y, w, h = e
            if all(isinstance(v, (int, float)) and math.isfinite(v) for v in (x, y, w, h)) and w > 0 and h > 0:
                wins[i] = (x, y, w, h)
        except (ValueError, TypeError):
            pass
    return wins


@ClassInfo({"D-Bus Interface": "org.mochi.Pet"})
class Bus(QObject):
    """Receives window rects pushed by kwin.js (Wayland won't let a normal app list other windows)."""
    def __init__(self, pet):
        super().__init__()
        self.pet = pet

    @Slot(str)
    def windows(self, js):
        try:
            self.pet.wins = parse_windows(js)
        except (ValueError, TypeError) as e:       # anyone on the session bus can call us; keep the last good list
            log.warning("ignored bad window payload: %s", e)


class Pet(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(S, S)
        self.t = self.vy = self.squash = self.blink = 0.0
        self.facing, self.hearts = 1, []            # hearts: [x, y, life]
        self.wins, self.support, self.vx, self.grounded = {}, None, 0.0, False   # wins: id -> (x, y, w, h); support: id we stand on
        self.next_blink, self.moved, self.press, self.mask_key = 2.0, False, None, None
        self.cfg = QSettings("mochi-pet", "mochi")
        self.theme = self.cfg.value("theme", "Kem")
        if self.theme not in THEMES: self.theme = "Kem"
        g = self.screen_geo()
        self.px, self.py = random.uniform(g.left() + 80, g.right() - 240), g.top() - 100
        self.set_state("fall")
        self.clock = QElapsedTimer(); self.clock.start()   # real frame time, see tick()
        self.timer = QTimer(self, interval=33, timeout=self.tick)
        self.timer.start()
        self.bus = Bus(self)
        sb = QDBusConnection.sessionBus()
        if not sb.isConnected():
            log.warning("no session bus: walking on the screen floor only")
        elif not sb.registerService("org.mochi.Pet"):
            sys.exit("mochi: already running (org.mochi.Pet is taken)")
        else:
            sb.registerObject("/pet", self.bus, QDBusConnection.ExportAllSlots)
            self.load_kwin_script(sb)

    def load_kwin_script(self, sb):
        # ponytail: KDE only; elsewhere the pet just walks on the screen floor
        kw = QDBusInterface("org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting", sb)
        if not kw.isValid():
            log.info("KWin not available: walking on the screen floor only")
            return
        kw.call("unloadScript", "mochi")                       # a crashed run may have left it loaded
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kwin.js")
        r = kw.call("loadScript", path, "mochi")
        args = r.arguments()
        if r.type() == QDBusMessage.MessageType.ErrorMessage or not args or args[0] < 0:
            log.error("KWin loadScript failed: %s", r.errorMessage() or args)
            return
        QApplication.instance().aboutToQuit.connect(lambda: kw.call("unloadScript", "mochi"))
        r = QDBusInterface("org.kde.KWin", f"/Scripting/Script{args[0]}", "org.kde.kwin.Script", sb).call("run")
        if r.type() == QDBusMessage.MessageType.ErrorMessage:
            log.error("KWin script run failed: %s", r.errorMessage())

    # ---- behaviour -------------------------------------------------------
    def pick_next(self):
        w = {"idle": 4, "walk": 3, "sleep": 1, "groom": 2, "yawn": 1, "stretch": 1, "chase": 1}
        w.pop(self.state, None)   # never repeat the action it just finished
        return random.choices(list(w), list(w.values()))[0]

    def set_state(self, s):
        self.state = s
        lo, hi = DUR.get(s, (0, 0))
        self.until = self.t + random.uniform(lo, hi)
        self.began, self.dur = self.t, max(self.until - self.t, 1e-3)          # for one-shot animations
        if s == "walk":
            self.facing = random.choice((-1, 1))

    def screen_geo(self):
        c = QPoint(int(getattr(self, "px", 0)) + S // 2, int(getattr(self, "py", 0)) + FEET)
        return (QGuiApplication.screenAt(c) or QGuiApplication.primaryScreen()).availableGeometry()

    def tick(self):
        dt = min(self.clock.restart() / 1000, MAX_DT)
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
            riding = wid is not None and wid == self.support and self.vy >= 0   # already standing on this window
            if riding:
                self.py = floor                                    # ride it while it moves
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
                self.support, riding = wid, True
            if riding:                                             # on the floor or a window: free to move
                self.grounded = True
                if self.state == "walk":
                    self.walk(dt, g, cx, wid)
                elif self.state == "chase":
                    self.chase(dt, g, cx, wid)
            if self.state in DUR and self.t > self.until:
                nxt = {"happy": "idle", "yawn": random.choice(("sleep", "idle"))}    # a yawn often ends in a nap
                self.set_state(nxt.get(self.state) or self.pick_next())
            self.move(int(self.px), int(self.py))
        self.update_mask()
        self.update()

    def surface(self, cx, feet, g):
        """(window-y of the surface under the feet, id of the window it is or None for the screen floor)"""
        best, wid = g.bottom() + 1, None
        for i, (x, y, w, _h) in self.wins.items():
            if x + 24 <= cx <= x + w - 24 and y >= g.top() + HEAD and y < best and (y >= feet - 6 or i == self.support) \
                    and not self.covered(i, cx, y + 1):
                best, wid = y, i
        return best - FEET, wid

    def covered(self, i, x, y):
        """is point (x, y) hidden under a window stacked above window i? (self.wins is ordered bottom -> top)"""
        above = False
        for j, (wx, wy, ww, wh) in self.wins.items():
            if above and wx <= x <= wx + ww and wy <= y < wy + wh: return True
            above = above or j == i
        return False

    def span(self, g, wid):
        """x-range the centre may walk in: the screen, or the top of the window we stand on"""
        lo, hi = g.left() + 50, g.right() - 50
        if wid is not None:
            x, _, w, _ = self.wins[wid]
            lo, hi = max(lo, x + 34), min(hi, x + w - 34)
        return lo, hi

    def chase(self, dt, g, cx, wid):
        lo, hi = self.span(g, wid)
        dx = max(lo, min(hi, QCursor.pos().x())) - cx
        if abs(dx) < 45:
            self.set_state("happy")                                # caught it!
            return
        self.facing = 1 if dx > 0 else -1
        self.px += self.facing * 2 * WALK_SPEED * dt

    def walk(self, dt, g, cx, wid):
        step = self.facing * WALK_SPEED * dt
        self.px += step; cx += step
        lo, hi = self.span(g, wid)
        if wid is None and random.random() < 0.004:                              # on the floor: sometimes hop onto a nearby window
            self.hop_to(cx, self.py + FEET, g)
        if cx < lo or cx > hi:
            out = -1 if cx < lo else 1
            if wid is not None and random.random() < 0.4:          # hop off the window edge
                self.facing, self.vx, self.vy, self.support = out, out * 140, -260, None
            else:
                self.facing = -out

    def hop_to(self, cx, feet, g):
        for i, (x, y, w, _h) in self.wins.items():
            up = feet - y                                          # how high the top is above our feet
            if 20 < up < 200 and y >= g.top() + HEAD and x - 120 < cx < x + w + 120:
                tx = max(x + 40, min(x + w - 40, cx))              # aim for a spot on top, then solve the arc
                if self.covered(i, tx, y + 1): continue            # that spot is under another window
                vy = -math.sqrt(2 * GRAVITY * (up + 40))
                t = (-vy + math.sqrt(vy * vy - 2 * GRAVITY * up)) / GRAVITY
                self.vy, self.vx = vy, (tx - cx) / t
                if tx != cx: self.facing = 1 if tx > cx else -1
                return

    def update_mask(self):
        # clip the window to the pet's silhouette so clicks pass through the transparent rest
        c, f, sleep, stretch = S // 2, -self.facing, self.state == "sleep", self.state == "stretch"
        key = (f, sleep, stretch, tuple((int(x), int(y)) for x, y, _ in self.hearts))
        if key == self.mask_key: return
        self.mask_key = key
        r = QRegion(c - 72, FEET - 88, 144, 100, QRegion.Ellipse)                   # body
        r += QRegion(c - 66, FEET - 106, 132, 60)                                  # ears
        r += QRegion(c - 60, FEET - 14, 120, 28)                                    # feet + shadow
        r += QRegion(min(c + f * 30, c + f * 100), FEET - 92, 70, 96)               # tail
        if sleep: r += QRegion(c + 28, FEET - 124, 48, 44)                         # zzz
        if stretch: r += r.translated(-f * 10, 0) + r.translated(0, -8)            # the pose leans forward and lifts its bum
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
        colors = m.addMenu("Màu")
        for name in THEMES:
            a = colors.addAction(name)
            a.setCheckable(True); a.setChecked(name == self.theme)
            a.triggered.connect(lambda _, n=name: self.set_theme(n))
        m.addAction("Ngủ", lambda: self.set_state("sleep"))
        m.addAction("Gọi về", self.bring_back)
        m.addAction("Thoát", QApplication.quit)
        m.exec(e.globalPos())

    def bring_back(self):
        """drop the pet in from the top of the primary screen (e.g. it got lost off-screen)"""
        g = QGuiApplication.primaryScreen().availableGeometry()
        self.px, self.py, self.vy, self.vx, self.support = g.center().x() - S / 2, g.top() - 100, 0.0, 0.0, None
        self.set_state("fall")

    def set_theme(self, name):
        self.theme = name
        self.cfg.setValue("theme", name)

    # ---- drawing ---------------------------------------------------------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.translate(S / 2, FEET)
        t, st = self.t, self.state
        up = st in ("fall", "drag")
        th = THEMES[self.theme]
        DARK, TAIL, EAR, PINK = (QColor(th[k]) for k in ("eye", "tail", "ear", "inner"))
        if self.grounded:                                                          # shadow only when standing
            p.setPen(Qt.NoPen); p.setBrush(QColor(0, 0, 0, 38)); p.drawEllipse(QPointF(0, 1), 46, 6)

        hop, sy = 0.0, 1 + 0.025 * math.sin(t * 2.4)
        if st == "walk": hop = abs(math.sin(t * 9)) * 7
        elif st == "sleep": sy = 1 + 0.04 * math.sin(t * 1.2)
        elif st == "drag": sy = 1.08
        o = math.sin(math.pi * min(1, (t - self.began) / self.dur))               # 0 -> 1 -> 0 over a one-shot move
        tilt = shift = 0.0
        if st == "stretch": sy -= .14 * o; tilt = 4 * o; shift = 8 * o                           # stretch forward, bum up
        elif st == "yawn": sy += .05 * o; tilt = -5 * o
        elif st == "chase": hop = abs(math.sin(t * 14)) * 9
        sy -= self.squash
        sx = 2 - sy if st != "drag" else .94        # keep volume: taller = thinner
        p.translate(shift * self.facing, -hop)
        p.rotate(tilt * self.facing)
        p.scale(-sx * self.facing, sy)                               # tail trails behind the walking direction

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
        g.setColorAt(0, QColor(th["top"])); g.setColorAt(1, QColor(th["bottom"]))
        p.setPen(Qt.NoPen); p.setBrush(QBrush(g)); p.drawEllipse(QRectF(-47, -80, 94, 76))

        # face
        for m in (-1, 1): blob(QColor(255, 157, 176, 120), m * 31, -37, 8, 4.5)
        cur = QCursor.pos() - self.pos() - QPoint(S // 2, FEET - 46)                 # eyes follow the cursor
        lx, ly = max(-1, min(1, cur.x() / 250)) * -2.5 * self.facing, max(-1, min(1, cur.y() / 250)) * 1.5
        pen = QPen(DARK, 3, Qt.SolidLine, Qt.RoundCap)
        for x in (-19, 19):
            if st in ("sleep", "yawn", "stretch", "groom") or self.blink > 0:
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
        elif st == "yawn": blob(PINK.darker(150), 0, -33, 4 + 3 * o, 2 + 8 * o)
        else:
            mouth = QPainterPath(QPointF(-5, -38)); mouth.quadTo(-2.5, -33, 0, -38); mouth.quadTo(2.5, -33, 5, -38)
            p.setPen(QPen(DARK, 2, Qt.SolidLine, Qt.RoundCap)); p.setBrush(Qt.NoBrush); p.drawPath(mouth)

        if st == "groom":                                          # lick a paw, stroke the cheek
            lift = (.5 + .5 * math.sin(t * 9)) * min(1, o * 3)
            blob(TAIL, 27 - 5 * lift, -16 - 22 * lift, 8, 10)
            blob(PINK, 25 - 5 * lift, -24 - 22 * lift, 2.5, 2)

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
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(levelname)s: %(message)s")
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: app.quit())          # `mochi off` / Ctrl-C -> clean exit (unloads the KWin script)
    pet = Pet(); pet.show()
    sys.exit(app.exec())
