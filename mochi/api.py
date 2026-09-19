"""The public DBus API: lets other programs talk through the pet.

    gdbus call --session --dest org.mochi.Pet --object-path /pet --method org.mochi.Pet.showMessage "Build finished"

Anything on the session bus may call this, so every argument is validated and calls are rate-limited; a slot never raises."""
import functools
import logging
import time
from collections import deque
from typing import Any

from PySide6.QtCore import ClassInfo, QObject, Slot

from .bubble import clean_text
from .state import Expression, Motion, State

log = logging.getLogger("mochi")
SERVICE, PATH = "org.mochi.Pet", "/pet"
RATE_CALLS, RATE_SECS = 20, 10.0               # at most this many calls per window, across all methods
WARN_EVERY = 10.0
MIN_FOCUS, MAX_FOCUS = 1, 180                  # minutes accepted by startPomodoro
EXPRESSIONS = {"normal": State(), "happy": State(expression=Expression.HAPPY), "dizzy": State(Motion.WALK, Expression.DIZZY),
               "scared": State(expression=Expression.SCARED), "tired": State(expression=Expression.TIRED)}

_class_info: Any = ClassInfo                   # PySide6's type stubs declare ClassInfo without arguments


def guarded(fn):
    """turn a slot into one that refuses when there is no pet or too many calls, logs (rarely) instead of raising, and answers
    True only if the request was carried out"""
    @functools.wraps(fn)
    def run(self, arg):
        now = time.monotonic()
        while self.calls and now - self.calls[0] > RATE_SECS: self.calls.popleft()
        if self.pet is None or len(self.calls) >= RATE_CALLS: return self.refuse(now, "rate limit" if self.pet else "no pet")
        self.calls.append(now)
        try:
            return bool(fn(self, arg))
        except Exception as e:                 # untrusted input: never let an error escape into Qt's event dispatch
            return self.refuse(now, f"{fn.__name__} failed: {e}")
    return run


@_class_info({"D-Bus Interface": SERVICE})
class Api(QObject):
    def __init__(self, pet=None):
        super().__init__()
        self.pet, self.calls, self.refused_at, self.refused = pet, deque(), -WARN_EVERY, 0

    def refuse(self, now, why):
        self.refused += 1
        if now - self.refused_at >= WARN_EVERY:
            log.warning("DBus call refused: %s (%d since the last warning)", why, self.refused)
            self.refused_at, self.refused = now, 0
        return False

    @Slot(str, result=bool)
    @guarded
    def showMessage(self, text):
        text = clean_text(text)
        if not text: return False
        self.pet.say(text, urgent=True)
        return True

    @Slot(str, result=bool)
    @guarded
    def setExpression(self, name):
        state = EXPRESSIONS.get(str(name).strip().lower())
        if state is None or self.pet.state.motion in (Motion.DRAG, Motion.AIRBORNE): return False
        self.pet.enter(state)
        return True

    @Slot(str, result=bool)
    @guarded
    def notifyTaskFinished(self, task):
        task = clean_text(task)[:80]
        self.pet.say(f"Xong rồi: {task}" if task else "Xong rồi!", urgent=True)
        self.pet.celebrate()
        return True

    @Slot(str, result=bool)
    @guarded
    def setMode(self, name):
        return self.pet.set_mode(clean_text(name))

    @Slot(int, result=bool)
    @guarded
    def startPomodoro(self, minutes):
        if not MIN_FOCUS <= minutes <= MAX_FOCUS: return False
        self.pet.start_focus(minutes)
        return True
