"""The pet widget: what it does next, per-frame physics, and mouse input."""
import random

from PySide6.QtCore import QElapsedTimer, QPoint, Qt, QTimer
from PySide6.QtGui import QCursor, QGuiApplication, QPainter
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from . import physics
from .physics import FEET, GRAVITY, S, WALK_SPEED, Bounds
from .renderer import THEMES, paint, silhouette
from .settings import Settings

DUR = {"idle": (2, 5), "walk": (3, 8), "sleep": (8, 20), "happy": (1.4, 1.4),      # seconds per state
       "yawn": (1.8, 1.8), "stretch": (2.4, 2.4), "groom": (3, 4.5), "chase": (5, 9)}
MAX_DT = 0.05                       # cap one frame's time step so a stall can't launch the pet through a window


class Pet(QWidget):
    def __init__(self, settings=None):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(S, S)
        self.t = self.vy = self.squash = self.blink = 0.0
        self.facing, self.hearts = 1, []            # hearts: [x, y, life]
        self.wins, self.support, self.vx, self.grounded = {}, None, 0.0, False   # wins: id -> (x, y, w, h); support: id we stand on
        self.next_blink, self.moved, self.press, self.mask_key = 2.0, False, None, None
        self.cfg = settings or Settings()
        self.theme = self.cfg.theme
        g = self.screen_geo()
        self.px, self.py = random.uniform(g.left + 80, g.right - 240), g.top - 100
        self.set_state("fall")
        self.clock = QElapsedTimer(); self.clock.start()   # real frame time, see tick()
        self.timer = QTimer(self, interval=33, timeout=self.tick)
        self.timer.start()

    def set_windows(self, wins):
        self.wins = wins

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
        r = (QGuiApplication.screenAt(c) or QGuiApplication.primaryScreen()).availableGeometry()
        return Bounds(r.left(), r.top(), r.right(), r.bottom())

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
            floor, wid = physics.surface(self.wins, self.support, cx, self.py + FEET, g)
            riding = wid is not None and wid == self.support and self.vy >= 0   # already standing on this window
            if riding:
                self.py = floor                                    # ride it while it moves
            elif self.py < floor - 0.5 or self.vy < 0:             # airborne
                self.grounded = False
                self.vy += GRAVITY * dt
                self.py += self.vy * dt
                self.px = max(g.left - 40, min(g.right - S + 40, self.px + self.vx * dt))
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

    def chase(self, dt, g, cx, wid):
        lo, hi = physics.span(self.wins, g, wid)
        dx = max(lo, min(hi, QCursor.pos().x())) - cx
        if abs(dx) < 45:
            self.set_state("happy")                                # caught it!
            return
        self.facing = 1 if dx > 0 else -1
        self.px += self.facing * 2 * WALK_SPEED * dt

    def walk(self, dt, g, cx, wid):
        step = self.facing * WALK_SPEED * dt
        self.px += step; cx += step
        lo, hi = physics.span(self.wins, g, wid)
        if wid is None and random.random() < 0.004:                              # on the floor: sometimes hop onto a nearby window
            self.hop_to(cx, self.py + FEET, g)
        if cx < lo or cx > hi:
            out = -1 if cx < lo else 1
            if wid is not None and random.random() < 0.4:          # hop off the window edge
                self.facing, self.vx, self.vy, self.support = out, out * 140, -260, None
            else:
                self.facing = -out

    def hop_to(self, cx, feet, g):
        hop = physics.hop_target(self.wins, cx, feet, g)
        if hop:
            self.vx, self.vy, face = hop
            if face: self.facing = face

    def update_mask(self):
        # clip the window to the pet's silhouette so clicks pass through the transparent rest
        f, sleep, stretch = -self.facing, self.state == "sleep", self.state == "stretch"
        key = (f, sleep, stretch, tuple((int(x), int(y)) for x, y, _ in self.hearts))
        if key == self.mask_key: return
        self.mask_key = key
        self.setMask(silhouette(f, sleep, stretch, self.hearts))

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
        self.cfg.theme = name

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        paint(self, p)
