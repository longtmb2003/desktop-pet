"""Pure geometry: which surface the pet stands on, where it may walk, how it hops. No Qt, so it is unit-testable."""
import math
from typing import Any, NamedTuple

S, FEET = 160, 146                  # window size, y of the floor line inside the window
GRAVITY, WALK_SPEED = 1800, 55
HEAD = 190                          # a window must be this far below the screen top to be stood on

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
        if x + 24 <= cx <= x + w - 24 and y >= b.top + HEAD and y < best and (y >= feet - 6 or i == support) \
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
        if 20 < up < 200 and y >= b.top + HEAD and x - 120 < cx < x + w + 120:
            tx = max(x + 40, min(x + w - 40, cx))              # aim for a spot on top, then solve the arc
            if covered(wins, i, tx, y + 1): continue           # that spot is under another window
            vy = -math.sqrt(2 * GRAVITY * (up + 40))
            t = (-vy + math.sqrt(vy * vy - 2 * GRAVITY * up)) / GRAVITY
            return (tx - cx) / t, vy, (None if tx == cx else 1 if tx > cx else -1)
    return None
