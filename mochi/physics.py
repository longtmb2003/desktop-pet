"""Pure geometry: which surface the pet stands on, where it may walk, how it hops. No Qt, so it is unit-testable."""
import math
from collections import deque
from typing import Any, NamedTuple

S, FEET = 160, 146                  # window size, y of the floor line inside the window
GRAVITY, WALK_SPEED = 1800, 55
HEAD = 190                          # a window must be this far below the screen top to be stood on
# --- flight (px, seconds) -------------------------------------------------------------------------------
TERMINAL = 1800                     # gravity alone never speeds a fall past this (a faster *throw* is left alone)
WALL_PAD = 40                       # how far the window may overhang the screen edge before it bounces
HEAD_ROOM = 40                      # window-y of the top of the ears: the ceiling is b.top - HEAD_ROOM
BOUNCE_X, BOUNCE_Y = 0.55, 0.35     # fraction of normal speed kept after hitting a wall / ceiling / floor
FLOOR_FRICTION = 0.7                # sideways speed kept per floor bounce
IMPACT_DIZZY = 2000               # a hit harder than this (px/s, normal component) leaves the pet dizzy; free falls stay below it
REST_VY = 150                       # a floor bounce slower than this doesn't happen: the pet just settles
# --- throwing: release velocity from the last few mouse samples ---------------------------------------------
VEL_WINDOW = 0.12                   # only samples this recent (s) count: a mouse that stopped before release is a drop
THROW_MIN, THROW_MAX = 350, 2600    # slower than THROW_MIN is a plain drop; faster than THROW_MAX is clamped
SHAKE_WINDOW = 0.8                 # seconds of mouse history is_shake() gets to look at
MIN_W = 80                          # narrower windows can't hold the pet: span() would be empty and it would jitter

Wins = dict[Any, tuple[float, float, float, float]]     # id -> (x, y, w, h), ordered bottom -> top


class Bounds(NamedTuple):
    """Usable area of one screen, inclusive pixel edges (same convention as QRect.right()/bottom())."""
    left: int
    top: int
    right: int
    bottom: int


def covered(wins, i, x, y):
    """is point (x, y) hidden under a window stacked above window i? (wins is ordered bottom -> top)"""
    above = False
    for j, (wx, wy, ww, wh) in wins.items():
        if above and wx <= x <= wx + ww and wy <= y < wy + wh: return True
        above = above or j == i
    return False


def surface(wins, support, cx, feet, b):
    """(window-y of the surface under the feet, id of the window it is or None for the screen floor)"""
    best, wid = b.bottom + 1, None
    for i, (x, y, w, _h) in wins.items():
        if w >= MIN_W and x + 24 <= cx <= x + w - 24 and y >= b.top + HEAD and y < best and (y >= feet - 6 or i == support) \
                and not covered(wins, i, cx, y + 1):
            best, wid = y, i
    return best - FEET, wid


def span(wins, b, wid):
    """x-range the centre may walk in: the screen, or the top of the window we stand on"""
    lo, hi = b.left + 50, b.right - 50
    if wid is not None:
        x, _, w, _ = wins[wid]
        lo, hi = max(lo, x + 34), min(hi, x + w - 34)
    return lo, hi


def hop_target(wins, cx, feet, b):
    """(vx, vy, facing or None) for a jump from the floor onto a nearby, uncovered window top; None if there is none"""
    for i, (x, y, w, _h) in wins.items():
        up = feet - y                                          # how high the top is above our feet
        if w >= MIN_W and 20 < up < 200 and y >= b.top + HEAD and x - 120 < cx < x + w + 120:
            tx = max(x + 40, min(x + w - 40, cx))              # aim for a spot on top, then solve the arc
            if covered(wins, i, tx, y + 1): continue           # that spot is under another window
            vy = -math.sqrt(2 * GRAVITY * (up + 40))
            t = (-vy + math.sqrt(vy * vy - 2 * GRAVITY * up)) / GRAVITY
            return (tx - cx) / t, vy, (None if tx == cx else 1 if tx > cx else -1)
    return None


class DragTracker:
    """Release velocity of a dragged pet from the last few (time, x, y) mouse samples; times are monotonic seconds."""
    def __init__(self):
        self.samples = deque(maxlen=8)          # for the release velocity
        self.trail = deque()                    # the last SHAKE_WINDOW seconds, for shake detection

    def reset(self):
        self.samples.clear(); self.trail.clear()

    def add(self, t, x, y):
        self.samples.append((t, x, y))
        self.trail.append((t, x, y))
        while self.trail[0][0] < t - SHAKE_WINDOW: self.trail.popleft()

    def velocity(self, now):
        """(vx, vy) px/s over the last VEL_WINDOW, recent movement weighted more, clamped to THROW_MAX; (0, 0) if the mouse was still"""
        pts = [p for p in self.samples if now - p[0] <= VEL_WINDOW]
        sx = sy = sw = 0.0
        for (t0, x0, y0), (t1, x1, y1) in zip(pts, pts[1:], strict=False):
            if t1 <= t0: continue
            w = t1 - pts[0][0] + 1e-3                          # later segments weigh more
            sx += (x1 - x0) / (t1 - t0) * w; sy += (y1 - y0) / (t1 - t0) * w; sw += w
        if sw == 0: return 0.0, 0.0
        vx, vy = sx / sw, sy / sw
        speed = math.hypot(vx, vy)
        if speed > THROW_MAX: vx, vy = vx * THROW_MAX / speed, vy * THROW_MAX / speed
        return vx, vy


class Flight(NamedTuple):
    x: float
    y: float
    vx: float
    vy: float
    landed: bool        # came to rest on the surface this frame
    hit: bool           # touched a wall, the ceiling or the floor this frame (for the squash animation)
    impact: float       # normal speed (px/s) of the hardest hit this frame, 0 if none


def step_air(x, y, vx, vy, dt, floor, b):
    """One frame of flight for the pet window at (x, y): gravity, bouncing off the screen edges and ceiling, and off the
    surface whose window-y is `floor`. Bounces lose energy, and a floor bounce below REST_VY becomes a landing, so it always settles."""
    vy = min(vy + GRAVITY * dt, max(vy, TERMINAL))
    x, y = x + vx * dt, y + vy * dt
    impact, hit = 0.0, False
    lo, hi = b.left - WALL_PAD, b.right - S + WALL_PAD
    if x < lo and vx < 0 or x > hi and vx > 0:
        x, impact, hit, vx = (lo if x < lo else hi), abs(vx), True, -vx * BOUNCE_X
    ceiling = b.top - HEAD_ROOM
    if y < ceiling and vy < 0:
        y, impact, hit, vy = ceiling, max(impact, -vy), True, -vy * BOUNCE_Y
    if y >= floor and vy > 0:
        impact, hit = max(impact, vy), True
        if vy * BOUNCE_Y < REST_VY:
            return Flight(x, floor, 0.0, 0.0, True, True, impact)
        y, vy, vx = floor, -vy * BOUNCE_Y, vx * FLOOR_FRICTION
    return Flight(x, y, vx, vy, False, hit, impact)


def is_shake(trail, now):
    """Is the mouse being shaken right now?

    `trail` is the pointer history while the pet is held: [(t, x, y), ...] oldest first, monotonic seconds, pixels, covering the
    last SHAKE_WINDOW seconds up to `now`. Return True for a vigorous back-and-forth, False for an ordinary drag or a flick."""
    # TODO(human): decide what counts as a shake (direction reversals, minimum stroke length, speed...) and return True/False
    return False
