"""Persistent user settings, stored with QSettings. Every value is validated on the way out: a hand-edited or corrupt file
falls back to the default (or is clamped) instead of crashing the pet."""
from PySide6.QtCore import QSettings

from .renderer import THEMES


def _prop(key, default, lo=None, hi=None):
    """a typed setting: bools stay bools, numbers are clamped to [lo, hi], anything unparsable gives the default.
    (Qt's own `type=` conversion turns garbage into 0/False without saying so, so the raw value is parsed here.)"""
    kind = type(default)

    def get(self):
        v = self.qs.value(key, default)
        try:
            if kind is bool:
                if isinstance(v, bool): return v
                return {"true": True, "false": False, "1": True, "0": False}[str(v).strip().lower()]
            v = kind(v)
            return v if lo is None else max(lo, min(hi, v))
        except (KeyError, TypeError, ValueError):
            return default

    def set_(self, v): self.qs.setValue(key, v)
    return property(get, set_)


class Settings:
    def __init__(self, qs=None):
        self.qs = qs or QSettings("mochi-pet", "mochi")

    @property
    def theme(self):
        t = self.qs.value("theme", "Kem")
        return t if t in THEMES else "Kem"

    @theme.setter
    def theme(self, name):
        self.qs.setValue("theme", name)

    quiet = _prop("quiet", False)                       # manual Quiet Mode: no chatter, no sound, low FPS
    quiet_auto = _prop("quiet_auto", True)              # also go quiet while a fullscreen app is up
    chase = _prop("chase", True)                        # may the pet run after the cursor?
    monitor = _prop("monitor", True)                    # react to a busy CPU (needs psutil)
    sound = _prop("sound", True)                        # beep when a Pomodoro phase ends
    time_of_day = _prop("time_of_day", True)            # sleepier at night
    chatter = _prop("chatter", True)                    # now and then say something unprompted
    speed = _prop("speed", 1.0, 0.3, 3.0)               # walking speed multiplier
    activity = _prop("activity", 1.0, 0.3, 3.0)         # how often it picks something to do (higher = fidgets more)
    focus_min = _prop("focus_min", 25, 1, 180)          # Pomodoro focus length
    break_min = _prop("break_min", 5, 1, 60)            # Pomodoro break length
