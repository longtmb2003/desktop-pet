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
    POINT = auto()          # scolding: jabbing a finger at the user (the mouse pointer)
    WAG = auto()            # scolding: finger raised, wagging "no, no, no"
    LECTURE = auto()        # scolding: pacing and gesturing with both hands
    STOMP = auto()          # mischief on a window: bouncing up and down on it
    PEEK = auto()           # mischief: leaning over the window's edge to look down
    DANGLE = auto()         # mischief: sitting on the window's edge, legs swinging
    DANCE = auto()          # mischief: a little dance


@dataclass(frozen=True)
class State:
    motion: Motion = Motion.IDLE
    expression: Expression = Expression.NORMAL
    action: Action = Action.NONE


_ACTION_SECS = {Action.YAWN: (1.8, 1.8), Action.STRETCH: (2.4, 2.4), Action.GROOM: (3, 4.5), Action.CHASE: (5, 9),
                Action.FLIP: (0.55, 0.55), Action.PUSH: (1.2, 1.8), Action.WORK: (6, 12), Action.RANT: (3.5, 5.5),
                Action.POINT: (3, 4.5), Action.WAG: (3, 4.5), Action.LECTURE: (4, 6), Action.STOMP: (2.5, 4), Action.PEEK: (3, 4.5),
                Action.DANGLE: (4, 7), Action.DANCE: (3, 5)}
SCOLDING = (Action.POINT, Action.WAG, Action.LECTURE)                          # a character with arms may scold
MISCHIEF = (Action.STOMP, Action.PEEK, Action.DANGLE, Action.DANCE)             # what it gets up to on the window you are working in
_MOTION_SECS = {Motion.IDLE: (2, 5), Motion.WALK: (3, 8), Motion.SLEEP: (8, 20)}
# what the pet may do next: (motion, action) -> weight
_NEXT = {(Motion.IDLE, Action.NONE): 4, (Motion.WALK, Action.NONE): 3,
         (Motion.IDLE, Action.GROOM): 2, (Motion.IDLE, Action.YAWN): 1, (Motion.IDLE, Action.STRETCH): 1,
         (Motion.WALK, Action.CHASE): 1}
BEHAVIORS = _NEXT                                            # what a pet does when its definition doesn't say otherwise
BEHAVIOR_NAMES = {"idle": (Motion.IDLE, Action.NONE), "walk": (Motion.WALK, Action.NONE), "sleep": (Motion.SLEEP, Action.NONE),
                  "groom": (Motion.IDLE, Action.GROOM), "yawn": (Motion.IDLE, Action.YAWN), "stretch": (Motion.IDLE, Action.STRETCH),
                  "chase": (Motion.WALK, Action.CHASE), "rant": (Motion.IDLE, Action.RANT), "point": (Motion.IDLE, Action.POINT),
                  "wag": (Motion.IDLE, Action.WAG), "lecture": (Motion.IDLE, Action.LECTURE)}      # the names a pet pack may use


def duration(s):
    """(min, max) seconds before `s` ends by itself, or None when it lasts until something else happens"""
    if s.motion in (Motion.AIRBORNE, Motion.DRAG): return None      # these end when the pet lands / is let go
    if s.action in _ACTION_SECS: return _ACTION_SECS[s.action]
    if s.expression is Expression.HAPPY: return (1.4, 1.4)
    if s.expression is Expression.DIZZY: return (3.5, 3.5)
    return _MOTION_SECS.get(s.motion)


def is_night(hour):
    """the evening and night (from 22:00 until 05:59), when it is calmer"""
    return hour >= 22 or hour < 6


CHASE = (Motion.WALK, Action.CHASE)
SLEEP = (Motion.SLEEP, Action.NONE)


def pick_next(s, rng=random, hour=None, chase=True, weights=None):
    """a random new behaviour, never the one `s` just finished, and never sleep: it only sleeps on a schedule, or when the screen
    locks or the computer sleeps (sleep.py) or when told to. `hour` (local, 0-23) makes chasing less likely in the evening and at
    night; None = no time-of-day effect. chase=False never picks a chase."""
    weights = weights or BEHAVIORS
    awake = {k: v for k, v in weights.items() if k != SLEEP} or dict(weights)
    w = {k: v for k, v in awake.items() if k != (s.motion, s.action)} or dict(awake)         # (a pet with one behaviour repeats it)
    if not chase: w.pop(CHASE, None)
    if hour is not None and is_night(hour) and CHASE in w: w[CHASE] *= 0.25
    motion, action = rng.choices(list(w) or [(Motion.IDLE, Action.NONE)], list(w.values()) or [1])[0]
    return State(motion, action=action)


def after(s, rng=random, hour=None, chase=True, weights=None):
    """the state that follows `s` once its timer runs out"""
    if s.expression in (Expression.HAPPY, Expression.DIZZY): return State()
    if s.action is Action.YAWN: return State()                                        # a yawn is just a yawn: no dozing off
    if s.action is Action.PUSH: return State(rng.choice((Motion.WALK, Motion.IDLE)))     # gives up: turns round or sits down
    return pick_next(s, rng, hour, chase, weights)


def ends_at(s, now, rng=random, activity=1.0):
    """absolute time `s` ends, `math.inf` if it never does. `activity` > 1 makes the pet change what it's doing more often (only
    the idle/walk/sleep stretches are scaled; one-shot animations and reactions keep their length)"""
    d = duration(s)
    if not d: return math.inf
    scale = 1 / activity if s.action is Action.NONE and s.expression is Expression.NORMAL else 1.0
    return now + rng.uniform(*d) * scale
