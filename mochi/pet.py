"""The pet widget: what it does next, per-frame physics, and mouse input."""
import math
import random
import time
from datetime import datetime

from PySide6.QtCore import QElapsedTimer, QFileSystemWatcher, QPoint, Qt, QTimer, QUrl
from PySide6.QtGui import QCursor, QDesktopServices, QGuiApplication, QPainter, QTransform
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from . import autostart, desktop, modes, monitor, physics, sleep
from . import reminders as rem
from .bubble import SpeechBubble
from .pomodoro import Pomodoro
from .reminders_dialog import RemindersDialog
from .pets import MOCHI, available
from .physics import IMPACT_DIZZY, THROW_MIN, Bounds, DragTracker
from .renderer import THEMES, paint, silhouette
from .settings import Settings
from .settings_dialog import SettingsDialog
from .sprite import paint_sprite, sprite_mask, sprite_mask_key
from .sound import chime
from .state import Action, Expression, Motion, State, after, ends_at

PUSH_CHANCE = 0.5                  # of the edge encounters that aren't a hop off, how many are a push against the "wall"
CLICK_DELAY_MS = 250                # a click waits this long for a second click before it counts as a pet
LOW_FPS_MS = 50                     # frame interval (ms) when asleep, or resting in Quiet Mode / on a busy CPU
MAX_DT = 0.05                       # cap one frame's time step so a stall can't launch the pet through a window


class Pet(QWidget):
    def __init__(self, settings=None, pets=None):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.t = self.vy = self.squash = self.blink = 0.0
        self.facing, self.hearts = 1, []            # hearts: [x, y, life]
        self.wins, self.support, self.vx, self.grounded = {}, None, 0.0, False   # wins: id -> (x, y, w, h); support: id we stand on
        self.next_blink, self.moved, self.press, self.mask_key = 2.0, False, None, None
        self.paused, self.drag, self.shaken = False, DragTracker(), False
        self.cfg = settings or Settings()
        self.theme = self.cfg.theme
        self.pets = pets if pets is not None else available()          # id -> PetDef
        self.defn, self.scale = self.pets.get(self.cfg.pet, MOCHI), self.cfg.scale
        self.fit_size()
        g = self.screen_geo()
        self.px, self.py = random.uniform(g.left + 80, g.right - 240 * self.scale), g.top - 100
        self.enter(State(Motion.AIRBORNE))
        self.clock = QElapsedTimer(); self.clock.start()   # real frame time, see tick()
        self.setAcceptDrops(True)
        self.desk_items, self.desk_watch = None, QFileSystemWatcher(self)     # what is on the desktop, refreshed when the folder changes
        self.desk_watch.directoryChanged.connect(lambda _: setattr(self, "desk_items", None))
        self.sched, self.rem_raw, self.pending, self.next_check = rem.Scheduler(rem.parse(self.cfg.reminders)), self.cfg.reminders, [], 0.0
        self.pomo, self.hot, self.cpu, self.read_cpu = Pomodoro(), False, monitor.Hysteresis(), monitor.cpu_percent
        self.mon_timer = QTimer(self, interval=monitor.POLL_MS, timeout=self.poll_cpu)
        self.last_touch, self.now_hour = -1e9, lambda: datetime.now().hour      # local time zone; tests replace now_hour
        self.now_time = lambda: datetime.now().time()
        self.locked = self.suspended = False                                    # told by the PowerWatcher (power.py)
        self.sleeping_for, self.power = "", None                                # why it fell asleep by itself: "system" | "nap" | "night"
        self.bubble, self.fullscreen = SpeechBubble(), False    # fullscreen: pushed by the platform (kwin.js)
        self.next_chat = random.uniform(60, 180)
        self.click_timer = QTimer(self, singleShot=True, interval=CLICK_DELAY_MS, timeout=self.pet_it)
        self.timer = QTimer(self, interval=33, timeout=self.tick)
        self.timer.start()
        self.sync_monitor()
        QGuiApplication.instance().screenRemoved.connect(lambda _: QTimer.singleShot(0, self.ensure_visible))

    def set_windows(self, wins):
        self.wins = wins

    # ---- behaviour -------------------------------------------------------
    def enter(self, state):
        self.state = state
        self.until = ends_at(state, self.t, activity=self.cfg.activity)
        self.began, self.dur = self.t, max(min(self.until - self.t, 1e9), 1e-3)   # for one-shot animations
        if state.motion is Motion.WALK and state.action is Action.NONE:
            self.facing = random.choice((-1, 1))
        if state.action is Action.RANT and hasattr(self, "bubble"): self.say(random.choice(self.defn.chatter), chatter=True)

    def fit_size(self):
        """derive the window size and floor/head geometry from the current pet definition and scale"""
        d, k = self.defn, self.scale
        self.size, self.feet, self.top = round(d.size * k), round(d.feet * k), round(d.top * k)
        self.head, self.ceiling, self.walk_speed = (d.height + 84) * k, self.top, d.walk_speed * k
        self.setFixedSize(self.size, self.size)
        self.mask_key = None

    def change_pet(self, defn, scale):
        """switch character and/or size on the fly, keeping the feet where they are"""
        cx, fy = self.px + self.size / 2, self.py + self.feet
        self.defn, self.scale = defn, scale
        self.fit_size()
        self.px, self.py = cx - self.size / 2, fy - self.feet
        self.move(int(self.px), int(self.py))
        self.bubble.dismiss()
        self.next_chat = min(self.next_chat, self.t + random.uniform(30, 90))

    def screen_geo(self):
        c = QPoint(int(getattr(self, "px", 0)) + self.size // 2, int(getattr(self, "py", 0)) + self.feet)
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
        if self.state.motion is not Motion.DRAG:
            g = self.screen_geo()
            cx = self.px + self.size / 2
            floor, wid = physics.surface(self.wins, self.support, cx, self.py + self.feet, g, self.feet, self.head)
            riding = wid is not None and wid == self.support and self.vy >= 0   # already standing on this window
            if riding:
                self.py = floor                                    # ride it while it moves
            elif self.py < floor - 0.5 or self.vy < 0 or (self.state.motion is Motion.AIRBORNE and self.vx != 0):   # airborne
                self.grounded = False
                if self.support is not None and self.support not in self.wins and self.state.motion is not Motion.AIRBORNE:
                    self.support, self.vx, self.vy = None, 0.0, 0.0                 # the ground vanished under its feet
                    self.enter(State(Motion.AIRBORNE, Expression.SCARED))
                    self.say(self.defn.scream, urgent=True)
                f = physics.step_air(self.px, self.py, self.vx, self.vy, dt, floor, g, self.size, self.ceiling)
                self.px, self.py, self.vx, self.vy = f.x, f.y, f.vx, f.vy
                if f.hit: self.squash = 0.3
                calm_or_scared = self.state.expression in (Expression.NORMAL, Expression.SCARED)
                if f.impact >= IMPACT_DIZZY and self.state.motion is Motion.AIRBORNE and calm_or_scared:
                    self.enter(State(Motion.AIRBORNE, Expression.DIZZY))
                if f.landed:
                    self.support, self.grounded = wid, True
                    self.land()
            else:
                self.support, riding = wid, True
                self.land()
            if riding:                                             # on the floor or a window: free to move
                self.grounded = True
                if self.state.motion is Motion.WALK:
                    if self.state.action is Action.CHASE:
                        self.chase(dt, g, cx, wid)
                    elif self.state.action is Action.NONE:
                        self.walk(dt, g, cx, wid)                           # (a PUSH stands still)
            if self.t > self.until:
                edge = self.facing if self.state.action is Action.PUSH else 0
                self.enter(self.next_state())
                if edge: self.facing = -edge                                # after shoving the edge, never walk straight back into it
            self.move(int(self.px), int(self.py))
        if self.pomo.active: self.pomodoro_event(self.pomo.poll())
        if self.t >= self.next_check: self.next_check = self.t + 1.0; self.check_reminders(); self.check_sleep()
        if self.t > self.next_chat:
            self.next_chat = self.t + random.uniform(120, 300)
            if self.state.motion in (Motion.IDLE, Motion.WALK): self.say(self.idle_remark(), chatter=True)
        self.retune()
        if self.bubble.isVisible(): self.bubble.follow(self.px, self.py, self.screen_geo(), self.size, self.top)
        self.update_mask()
        self.update()

    def hour(self):
        """local hour for time-of-day habits, or None when they don't apply: switched off, or the user is playing with the pet
        (it is never nudged to sleep while being handled)"""
        return self.now_hour() if self.cfg.time_of_day and self.t - self.last_touch > 60 else None

    def apply_settings(self):
        """a setting changed: bring the running pet in line (CPU watching, frame rate)"""
        self.sync_monitor()
        if self.cfg.reminders != self.rem_raw:
            self.rem_raw = self.cfg.reminders; self.sched.replace(rem.parse(self.rem_raw))
        pd = self.pets.get(self.cfg.pet, self.defn)
        if pd is not self.defn or self.cfg.scale != self.scale: self.change_pet(pd, self.cfg.scale)
        self.retune()

    # ---- modes -----------------------------------------------------------
    def mode(self):
        """the active Mode (Bình thường if the saved one no longer exists)"""
        m = modes.available(self.cfg.custom_modes)
        return m.get(self.cfg.mode) or m["normal"]

    # ---- sleep -----------------------------------------------------------
    def sleep_reason(self):
        """why it should be asleep now: "system" (screen locked / computer sleeping), "nap", "night", or "" (awake)"""
        if self.cfg.sleep_system and (self.locked or self.suspended): return "system"
        return sleep.scheduled(self.now_time(), self.cfg)

    def attach_power(self, watcher):
        self.power = watcher

    def on_lock(self, locked):
        self.locked = locked
        self.check_sleep()

    def on_suspend(self, going_to_sleep):
        self.suspended = going_to_sleep
        self.check_sleep()

    def check_sleep(self):
        """put it to sleep when it should be, and wake it (yawn, greeting) when the reason has passed. Sleep it chose itself only:
        one you asked for from the menu is left alone"""
        reason = self.sleep_reason()
        if reason:
            if self.sleeping_for and self.state.motion is Motion.SLEEP: self.sleeping_for = reason        # (say, a nap began while locked)
            settled = self.grounded and self.state.motion in (Motion.IDLE, Motion.WALK)
            handled = reason != "system" and self.t - self.last_touch <= 20                # not while it is being played with
            if settled and not handled and not (reason != "system" and self.pomo.focusing):
                self.sleeping_for = reason
                self.enter(State(Motion.SLEEP))
        elif self.sleeping_for:
            was, self.sleeping_for = self.sleeping_for, ""
            if self.state.motion is Motion.SLEEP:
                self.enter(State(action=Action.YAWN))
                self.say("Chào mừng bạn quay lại!" if was == "system" else "Ưm... dậy rồi!", chatter=True)

    def stay_state(self):
        """what keeps the pet doing one thing: asleep (screen locked, computer asleep, nap or night), a Pomodoro focus, or the
        active mode. None if nothing does"""
        if not self.grounded: return None
        reason, stay = self.sleep_reason(), self.mode().stay
        if reason == "system": return State(Motion.SLEEP)
        if self.pomo.focusing: return State(action=Action.WORK)
        idle_for_a_while = self.t - self.last_touch > 20                                 # (not right after being played with)
        if reason and idle_for_a_while: return State(Motion.SLEEP)
        if stay == "work": return State(action=Action.WORK)
        if stay == "sleep" and idle_for_a_while: return State(Motion.SLEEP)
        return None

    def next_state(self):
        """the state after the current one runs out"""
        s = self.stay_state()
        if s == State(Motion.SLEEP) and self.sleep_reason(): self.sleeping_for = self.sleep_reason()      # so it wakes when that ends
        return s or after(self.state, hour=self.hour(), chase=self.cfg.chase,
                          weights=modes.weights(self.defn.behaviors, self.mode().boost))

    def find_mode(self, key):
        """a mode id from an id or a name (any case), or None"""
        all_ = modes.available(self.cfg.custom_modes)
        key = str(key).strip()
        return key if key in all_ else next((i for i, m in all_.items() if m.name.lower() == key.lower()), None)

    def set_mode(self, key):
        """switch mode: apply its settings, and keep the pet at what it asks for. False if there is no such mode"""
        mid = self.find_mode(key)
        if mid is None: return False
        m = modes.available(self.cfg.custom_modes)[mid]
        for k, v in m.values.items(): setattr(self.cfg, k, v)
        self.cfg.mode = mid
        self.apply_settings()
        if getattr(self, "dialog", None) is not None: self.dialog.reload()
        if self.state.motion in (Motion.IDLE, Motion.WALK, Motion.SLEEP) and (s := self.stay_state()): self.enter(s)
        self.say(f"Chế độ: {m.name}", urgent=True)
        return True

    def save_mode(self, name):
        """keep the current settings as a mode of the user's own, and switch to it; ValueError if the name is empty"""
        current = {k: getattr(self.cfg, k) for k in modes.KEYS}
        new = modes.snapshot(name, current, self.mode())
        mine = {i: m for i, m in modes.available(self.cfg.custom_modes).items() if not m.builtin}
        if new.id not in mine and len(mine) >= modes.MAX_CUSTOM: raise ValueError(f"at most {modes.MAX_CUSTOM} modes of your own")
        mine[new.id] = new
        self.cfg.custom_modes = modes.dump_custom(mine); self.cfg.mode = new.id
        if getattr(self, "dialog", None) is not None: self.dialog.reload()
        return new

    def delete_mode(self, mid):
        mine = {i: m for i, m in modes.available(self.cfg.custom_modes).items() if not m.builtin}
        if mid not in mine: return False
        del mine[mid]
        self.cfg.custom_modes = modes.dump_custom(mine)
        if self.cfg.mode == mid: self.cfg.mode = "normal"                     # the settings stay as they are; only the label goes
        if getattr(self, "dialog", None) is not None: self.dialog.reload()
        return True

    def ask_mode_name(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Lưu chế độ", "Tên chế độ mới (lưu các cài đặt hiện tại):")
        if ok and name.strip():
            try:
                self.save_mode(name)
            except ValueError as e:
                self.say(str(e), urgent=True)

    # ---- the desktop -----------------------------------------------------
    def desktop_items(self):
        """[(path, name)] on the desktop, cached until the folder changes"""
        if self.desk_items is None:
            d = desktop.desktop_dir()
            self.desk_items = desktop.items(d)
            if d.is_dir() and str(d) not in self.desk_watch.directories(): self.desk_watch.addPath(str(d))
        return self.desk_items

    def idle_remark(self):
        """something to say when nothing is going on: usually its own chatter, sometimes about a thing on the desktop"""
        items = self.desktop_items() if self.cfg.desktop else []
        if items and random.random() < 0.3: return self.defn.desktop_remark.replace("{name}", random.choice(items)[1])
        return random.choice(self.defn.chatter)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()                 # files dragged from the desktop or a file manager

    def dropEvent(self, e):
        """something was dropped on the pet: it only reacts (never opens, moves or deletes what was dropped)"""
        names = [QUrl(u).fileName() or u.toString() for u in e.mimeData().urls()][:50]
        e.acceptProposedAction()
        self.react_to_drop(names)

    def react_to_drop(self, names):
        self.say(self.defn.drop.replace("{name}", desktop.summary(names)), urgent=True)
        if self.grounded and self.state.motion in (Motion.IDLE, Motion.WALK, Motion.SLEEP):
            self.enter(State(expression=Expression.HAPPY)); self.vy = -320
            self.hearts += [[random.uniform(-30, 30), 11 - self.defn.height, 1.2 + random.random() * .5] for _ in range(3)]

    def open_desktop_item(self, path):
        """open one of the things on the desktop, as if it had been double-clicked (only what is really on the desktop)"""
        if not desktop.is_on_desktop(path): return False
        self.say(f"Mở {desktop.entry_name(path)} nhé!", urgent=True)
        if self.grounded and self.state.motion in (Motion.IDLE, Motion.WALK): self.vy = -320
        return QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def check_reminders(self):
        """once a second: say whatever reminders have come due (held back while a fullscreen app has Quiet Mode on)"""
        self.pending += self.sched.due()
        if self.pending and not (self.fullscreen and self.cfg.quiet_auto):
            due, self.pending = self.pending, []
            for r in due: self.remind(r)

    def remind(self, r):
        """say one reminder: a bubble that jumps the queue, a little hop to get attention, a chime unless quiet or muted"""
        self.say(f"Nhắc: {r.text}", urgent=True)
        if self.grounded and self.state.motion in (Motion.IDLE, Motion.WALK): self.vy = -320
        if self.cfg.sound and not self.quiet: chime()

    def open_reminders(self):
        if getattr(self, "reminders_dialog", None) is None: self.reminders_dialog = RemindersDialog(self)
        self.reminders_dialog.show(); self.reminders_dialog.raise_(); self.reminders_dialog.activateWindow()

    def open_settings(self):
        if getattr(self, "dialog", None) is None: self.dialog = SettingsDialog(self)
        self.dialog.show(); self.dialog.raise_(); self.dialog.activateWindow()

    def sync_monitor(self):
        """start or stop CPU watching to match the setting (and whether psutil is there at all)"""
        if self.cfg.monitor and monitor.AVAILABLE:
            if not self.mon_timer.isActive(): self.read_cpu(); self.mon_timer.start()     # the first reading only primes the counter
        else:
            self.mon_timer.stop(); self.cpu.on = self.hot = False

    def poll_cpu(self):
        v = self.read_cpu()
        if v is None: return
        was, self.hot = self.hot, self.cpu.update(v)
        if self.hot and not was: self.say("Máy nóng quá...", chatter=True)

    def retune(self):
        """frame rate: full speed by default, 20 fps while asleep, or resting when quiet or the CPU is busy; never while it moves
        under physics (airborne, dragged, mid-action), where bigger steps would show"""
        resting = self.grounded and self.state.motion in (Motion.IDLE, Motion.WALK) and self.state.action is Action.NONE
        ms = LOW_FPS_MS if self.state.motion is Motion.SLEEP or resting and (self.hot or self.quiet) else 33
        if self.timer.interval() != ms: self.timer.setInterval(ms)

    def start_focus(self, minutes=None):
        """begin a Pomodoro: `minutes` of focus (default from Settings), then a break"""
        self.pomo.start((minutes or self.cfg.focus_min) * 60, self.cfg.break_min * 60)
        self.say(f"Tập trung nào! {minutes or self.cfg.focus_min} phút", urgent=True)
        if self.grounded and self.state.motion in (Motion.IDLE, Motion.WALK, Motion.SLEEP): self.enter(State(action=Action.WORK))

    def celebrate(self):
        """a happy little hop (and a chime, unless quiet or muted); for good news from outside"""
        if self.grounded and self.state.motion in (Motion.IDLE, Motion.WALK, Motion.SLEEP):
            self.enter(State(expression=Expression.HAPPY)); self.vy = -420
        if self.cfg.sound and not self.quiet: chime()

    def pomodoro_event(self, ev):
        if ev is None: return
        msg = {"focus_done": f"Hết giờ tập trung! Nghỉ {self.cfg.break_min} phút nhé", "break_done": "Hết giờ nghỉ, làm tiếp nào?"}[ev]
        self.say(msg, urgent=True)
        if self.cfg.sound and not self.quiet: chime()
        if ev == "focus_done" and self.grounded and self.state.motion in (Motion.IDLE, Motion.WALK):
            self.enter(State(expression=Expression.HAPPY))

    @property
    def quiet(self):
        """Quiet Mode: switched on by the user, or automatically while a fullscreen app is up (if allowed)"""
        return self.cfg.quiet or (self.cfg.quiet_auto and self.fullscreen)

    def say(self, text, urgent=False, chatter=False):
        """show a speech bubble; unprompted chatter is suppressed in Quiet Mode or when switched off"""
        if chatter and (self.quiet or not self.cfg.chatter): return
        self.bubble.say(text, urgent)

    def closeEvent(self, e):
        self.bubble.close()
        for name in ("dialog", "reminders_dialog"):
            if getattr(self, name, None) is not None: getattr(self, name).close()
        super().closeEvent(e)

    def throw(self, vx, vy):
        """let go of the pet: a fast enough mouse movement carries over as velocity, otherwise it just drops"""
        if math.hypot(vx, vy) < THROW_MIN: vx = vy = 0.0
        self.vx, self.vy = vx, vy
        self.enter(State(Motion.AIRBORNE, self.state.expression))       # a shaken pet keeps its dizziness

    def land(self):
        """the pet came to rest on a surface: an AIRBORNE fall ends (a walker that hopped keeps walking)"""
        if self.state.motion is Motion.AIRBORNE:
            dizzy = self.state.expression is Expression.DIZZY            # a hard landing: get up and stagger about
            self.enter(State(Motion.WALK, Expression.DIZZY) if dizzy else State())

    def chase(self, dt, g, cx, wid):
        lo, hi = physics.span(self.wins, g, wid)
        dx = max(lo, min(hi, QCursor.pos().x())) - cx
        if abs(dx) < 45:
            self.enter(State(expression=Expression.HAPPY))         # caught it!
            return
        self.facing = 1 if dx > 0 else -1
        self.px += self.facing * 2 * self.walk_speed * self.cfg.speed * dt

    def walk(self, dt, g, cx, wid):
        dizzy = self.state.expression is Expression.DIZZY
        step = self.facing * self.walk_speed * self.cfg.speed * (0.6 if self.hot else 1) * dt      # too hot to hurry
        if dizzy:                                                                # half speed, swaying, changing its mind
            step = step / 2 + math.sin(self.t * 7) * 40 * dt
            if random.random() < 0.02: self.facing = -self.facing
        self.px += step; cx += step
        lo, hi = physics.span(self.wins, g, wid)
        if wid is None and not dizzy and random.random() < 0.004:                              # floor: sometimes hop onto a window
            self.hop_to(cx, self.py + self.feet, g)
        if cx < lo or cx > hi:
            out = -1 if cx < lo else 1
            if wid is not None and not dizzy and random.random() < 0.4:      # hop off the window edge
                self.facing, self.vx, self.vy, self.support = out, out * 140, -260, None
            elif not dizzy and random.random() < PUSH_CHANCE:
                self.px = (lo if out < 0 else hi) - self.size / 2                   # stop at the edge and shove against it
                self.facing = out
                self.enter(State(Motion.WALK, action=Action.PUSH))
            else:
                self.facing = -out

    def hop_to(self, cx, feet, g):
        hop = physics.hop_target(self.wins, cx, feet, g, self.head)
        if hop:
            self.vx, self.vy, face = hop
            if face: self.facing = face

    def update_mask(self):
        # clip the window to the pet's silhouette so clicks pass through the transparent rest
        if self.defn.kind == "sprite":
            key = (self.defn.id, self.scale, *sprite_mask_key(self))
            if key != self.mask_key: self.mask_key = key; self.setMask(sprite_mask(self))
            return
        f, sleep = -self.facing, self.state.motion is Motion.SLEEP
        stretch = self.state.action in (Action.STRETCH, Action.PUSH)             # both lean forward
        flip = self.state.action is Action.FLIP
        key = (self.scale, f, sleep, stretch, flip, tuple((int(x), int(y)) for x, y, _ in self.hearts))
        if key == self.mask_key: return
        self.mask_key = key
        region = silhouette(f, sleep, stretch, self.hearts, flip)
        self.setMask(region if self.scale == 1 else QTransform().scale(self.scale, self.scale).map(region))

    # ---- input -----------------------------------------------------------
    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton: return
        g = e.globalPosition().toPoint()
        self.press, self.moved, self.off = g, False, g - self.pos()
        self.drag.reset(); self.drag.add(time.monotonic(), g.x(), g.y())
        self.shaken = False
        self.last_touch = self.t

    def mouseMoveEvent(self, e):
        if self.press is None: return
        g = e.globalPosition().toPoint()
        if not self.moved and (g - self.press).manhattanLength() > 4:
            self.moved = True
            self.support, self.vx = None, 0.0
            self.enter(State(Motion.DRAG))
        if self.moved:
            now = time.monotonic()
            self.drag.add(now, g.x(), g.y())
            if not self.shaken and physics.is_shake(self.drag.trail, now):
                self.shaken = True
                self.enter(State(Motion.DRAG, Expression.DIZZY))         # shaken silly; it stays dizzy after the release
            p = g - self.off
            self.px, self.py, self.vy = p.x(), p.y(), 0.0
            self.move(p)

    def mouseReleaseEvent(self, e):
        if self.press is None: return
        self.press = None
        if self.moved:
            self.throw(*self.drag.velocity(time.monotonic()))
        else:
            self.click_timer.start()                         # a click = a pet, unless a second click turns it into a flip

    def pet_it(self):
        if self.press is not None or self.state.motion is Motion.DRAG or self.state.action is Action.FLIP: return
        self.enter(State(expression=Expression.HAPPY))
        self.vy = -420
        self.hearts += [[random.uniform(-30, 30), 11 - self.defn.height, 1.2 + random.random() * .5] for _ in range(4)]   # above its head

    def mouseDoubleClickEvent(self, e):
        self.click_timer.stop()                              # the first click's pet never happens
        if e.button() != Qt.LeftButton or not self.grounded or self.state.motion in (Motion.DRAG, Motion.AIRBORNE): return
        self.enter(State(action=Action.FLIP))
        self.vy = -physics.GRAVITY * self.dur / 2            # airborne for exactly the length of the flip
        self.hearts = []

    def contextMenuEvent(self, e):
        self.build_menu().exec(e.globalPos())

    def build_menu(self):
        m = QMenu(self)
        colors = m.addMenu("Màu")
        for name in THEMES:
            a = colors.addAction(name)
            a.setCheckable(True); a.setChecked(name == self.theme)
            a.triggered.connect(lambda _, n=name: self.set_theme(n))
        pm = m.addMenu("Pomodoro")
        pm.addAction(self.pomo.label()).setEnabled(False)
        if not self.pomo.active: pm.addAction(f"Bắt đầu ({self.cfg.focus_min} phút)", self.start_focus)
        elif self.pomo.paused: pm.addAction("Tiếp tục", self.pomo.resume)
        else: pm.addAction("Tạm dừng", self.pomo.pause)
        if self.pomo.active: pm.addAction("Đặt lại", self.pomo.reset)
        a = m.addAction("Chế độ yên lặng"); a.setCheckable(True); a.setChecked(self.cfg.quiet)
        a.toggled.connect(lambda on: (setattr(self.cfg, "quiet", on), self.apply_settings()))
        mm = m.addMenu("Chế độ")
        all_ = modes.available(self.cfg.custom_modes)
        for mid, md in all_.items():
            a = mm.addAction(md.name); a.setCheckable(True); a.setChecked(mid == self.mode().id)
            a.triggered.connect(lambda _, i=mid: self.set_mode(i))
        mm.addSeparator()
        mm.addAction("Lưu cài đặt hiện tại thành chế độ...", self.ask_mode_name)
        mine = [md for md in all_.values() if not md.builtin]
        if mine:
            rm = mm.addMenu("Xoá chế độ của tôi")
            for md in mine: rm.addAction(md.name, lambda i=md.id: self.delete_mode(i))
        m.addAction("Nhắc việc...", self.open_reminders)
        items = self.desktop_items()
        if items:
            dm = m.addMenu("Mở từ màn hình nền")
            for path, name in items[:30]: dm.addAction(name, lambda p=path: self.open_desktop_item(p))
        m.addAction("Cài đặt...", self.open_settings)
        if len(self.pets) > 1:
            who = m.addMenu("Nhân vật")
            for pid, d in self.pets.items():
                a = who.addAction(d.name); a.setCheckable(True); a.setChecked(pid == self.defn.id)
                a.triggered.connect(lambda _, i=pid: (setattr(self.cfg, "pet", i), self.apply_settings()))
        m.addAction("Ngủ", lambda: self.enter(State(Motion.SLEEP)))
        m.addAction("Gọi về", self.bring_back)
        a = m.addAction("Tạm dừng"); a.setCheckable(True); a.setChecked(self.paused); a.toggled.connect(self.set_paused)
        a = m.addAction("Tự chạy khi đăng nhập"); a.setCheckable(True); a.setChecked(autostart.is_enabled())
        a.toggled.connect(lambda on: autostart.enable() if on else autostart.disable())
        m.addAction("Thoát", QApplication.quit)
        return m

    def bring_back(self):
        """drop the pet in from the top of the primary screen (e.g. it got lost off-screen)"""
        g = QGuiApplication.primaryScreen().availableGeometry()
        self.px, self.py, self.vy, self.vx, self.support = g.center().x() - self.size / 2, g.top() - 100 * self.scale, 0.0, 0.0, None
        self.enter(State(Motion.AIRBORNE))

    def set_paused(self, on):
        """freeze the pet in place (timer stopped, so no CPU) or let it carry on"""
        self.paused = on
        if on:
            self.timer.stop()
        else:
            self.clock.restart()                                 # don't count the pause as one huge frame
            self.timer.start()

    def ensure_visible(self):
        """called when a screen goes away: if the pet was on it, bring it back"""
        c = QPoint(int(self.px) + self.size // 2, int(self.py) + self.feet)
        if self.state.motion is not Motion.DRAG and QGuiApplication.screenAt(c) is None:
            self.bring_back()

    def set_theme(self, name):
        self.theme = name
        self.cfg.theme = name

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self.scale != 1: p.scale(self.scale, self.scale)
        (paint_sprite if self.defn.kind == "sprite" else paint)(self, p)
