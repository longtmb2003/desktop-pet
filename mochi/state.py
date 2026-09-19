"""Behaviour state on three independent axes, plus how long each lasts and what follows it.

Separate axes mean "airborne and scared" needs no combined state like `scared_fall`."""
import math
import random
from dataclasses import dataclass
from enum import Enum, auto


class Motion(Enum):
    IDLE = auto()
    WALK = auto()
    DRAG = auto()
    AIRBORNE = auto()
    SLEEP = auto()


class Expression(Enum):
    NORMAL = auto()
    HAPPY = auto()
    DIZZY = auto()
    SCARED = auto()
    TIRED = auto()


class Action(Enum):
    NONE = auto()
    GROOM = auto()
    YAWN = auto()
    STRETCH = auto()
    CHASE = auto()
    FLIP = auto()
    PUSH = auto()
    WORK = auto()           # sitting at a tiny laptop: what it does during a Pomodoro focus
    RANT = auto()           # talking away (a sprite pet's special action: its face animates while it says something)


@dataclass(frozen=True)
class State:
    motion: Motion = Motion.IDLE
    expression: Expression = Expression.NORMAL
    action: Action = Action.NONE


_ACTION_SECS = {Action.YAWN: (1.8, 1.8), Action.STRETCH: (2.4, 2.4), Action.GROOM: (3, 4.5), Action.CHASE: (5, 9),
                Action.FLIP: (0.55, 0.55), Action.PUSH: (1.2, 1.8), Action.WORK: (6, 12), Action.RANT: (3.5, 5.5)}
_MOTION_SECS = {Motion.IDLE: (2, 5), Motion.WALK: (3, 8), Motion.SLEEP: (8, 20)}
# what the pet may do next: (motion, action) -> weight
_NEXT = {(Motion.IDLE, Action.NONE): 4, (Motion.WALK, Action.NONE): 3, (Motion.SLEEP, Action.NONE): 1,
         (Motion.IDLE, Action.GROOM): 2, (Motion.IDLE, Action.YAWN): 1, (Motion.IDLE, Action.STRETCH): 1,
         (Motion.WALK, Action.CHASE): 1}
BEHAVIORS = _NEXT                                            # what a pet does when its definition doesn't say otherwise
BEHAVIOR_NAMES = {"idle": (Motion.IDLE, Action.NONE), "walk": (Motion.WALK, Action.NONE), "sleep": (Motion.SLEEP, Action.NONE),
                  "groom": (Motion.IDLE, Action.GROOM), "yawn": (Motion.IDLE, Action.YAWN), "stretch": (Motion.IDLE, Action.STRETCH),
                  "chase": (Motion.WALK, Action.CHASE), "rant": (Motion.IDLE, Action.RANT)}      # the names a pet pack may use


def duration(s):
    """(min, max) seconds before `s` ends by itself, or None when it lasts until something else happens"""
    if s.motion in (Motion.AIRBORNE, Motion.DRAG): return None      # these end when the pet lands / is let go
    if s.action in _ACTION_SECS: return _ACTION_SECS[s.action]
    if s.expression is Expression.HAPPY: return (1.4, 1.4)
    if s.expression is Expression.DIZZY: return (3.5, 3.5)
    return _MOTION_SECS.get(s.motion)


def is_night(hour):
    """small hours (00:00-05:59) make it sleepy; the evening from 22:00 only makes it calmer"""
    return 0 <= hour < 6


CHASE = (Motion.WALK, Action.CHASE)
SLEEP = (Motion.SLEEP, Action.NONE)


def pick_next(s, rng=random, hour=None, chase=True, weights=None):
    """a random new behaviour, never the one `s` just finished. `hour` (local, 0-23) tilts the odds towards sleep in the small
    hours and away from chasing from 22:00 on; None = no time-of-day effect. chase=False never picks a chase."""
    weights = weights or BEHAVIORS
    w = {k: v for k, v in weights.items() if k != (s.motion, s.action)} or dict(weights)     # (a pet with one behaviour repeats it)
    if not chase: w.pop(CHASE, None)
    if hour is not None and (is_night(hour) or hour >= 22):
        if CHASE in w: w[CHASE] *= 0.25
        if is_night(hour) and SLEEP in w: w[SLEEP] *= 6
    motion, action = rng.choices(list(w) or [(Motion.IDLE, Action.NONE)], list(w.values()) or [1])[0]
    return State(motion, action=action)


def after(s, rng=random, hour=None, chase=True, weights=None):
    """the state that follows `s` once its timer runs out"""
    if s.expression in (Expression.HAPPY, Expression.DIZZY): return State()
    if s.action is Action.YAWN:                                                       # a yawn often ends in a nap
        return State(rng.choices((Motion.SLEEP, Motion.IDLE), (4, 1) if hour is not None and is_night(hour) else (1, 1))[0])
    if s.action is Action.PUSH: return State(rng.choice((Motion.WALK, Motion.IDLE)))     # gives up: turns round or sits down
    return pick_next(s, rng, hour, chase, weights)


def ends_at(s, now, rng=random, activity=1.0):
    """absolute time `s` ends, `math.inf` if it never does. `activity` > 1 makes the pet change what it's doing more often (only
    the idle/walk/sleep stretches are scaled; one-shot animations and reactions keep their length)"""
    d = duration(s)
    if not d: return math.inf
    scale = 1 / activity if s.action is Action.NONE and s.expression is Expression.NORMAL else 1.0
    return now + rng.uniform(*d) * scale
