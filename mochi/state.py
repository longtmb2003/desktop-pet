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


@dataclass(frozen=True)
class State:
    motion: Motion = Motion.IDLE
    expression: Expression = Expression.NORMAL
    action: Action = Action.NONE


_ACTION_SECS = {Action.YAWN: (1.8, 1.8), Action.STRETCH: (2.4, 2.4), Action.GROOM: (3, 4.5), Action.CHASE: (5, 9),
                Action.FLIP: (0.55, 0.55), Action.PUSH: (1.2, 1.8)}
_MOTION_SECS = {Motion.IDLE: (2, 5), Motion.WALK: (3, 8), Motion.SLEEP: (8, 20)}
# what the pet may do next: (motion, action) -> weight
_NEXT = {(Motion.IDLE, Action.NONE): 4, (Motion.WALK, Action.NONE): 3, (Motion.SLEEP, Action.NONE): 1,
         (Motion.IDLE, Action.GROOM): 2, (Motion.IDLE, Action.YAWN): 1, (Motion.IDLE, Action.STRETCH): 1,
         (Motion.WALK, Action.CHASE): 1}


def duration(s):
    """(min, max) seconds before `s` ends by itself, or None when it lasts until something else happens"""
    if s.motion in (Motion.AIRBORNE, Motion.DRAG): return None      # these end when the pet lands / is let go
    if s.action in _ACTION_SECS: return _ACTION_SECS[s.action]
    if s.expression is Expression.HAPPY: return (1.4, 1.4)
    if s.expression is Expression.DIZZY: return (3.5, 3.5)
    return _MOTION_SECS.get(s.motion)


def pick_next(s, rng=random):
    """a random new behaviour, never the one `s` just finished"""
    w = {k: v for k, v in _NEXT.items() if k != (s.motion, s.action)}
    motion, action = rng.choices(list(w), list(w.values()))[0]
    return State(motion, action=action)


def after(s, rng=random):
    """the state that follows `s` once its timer runs out"""
    if s.expression in (Expression.HAPPY, Expression.DIZZY): return State()
    if s.action is Action.YAWN: return State(rng.choice((Motion.SLEEP, Motion.IDLE)))    # a yawn often ends in a nap
    if s.action is Action.PUSH: return State(rng.choice((Motion.WALK, Motion.IDLE)))     # gives up: turns round or sits down
    return pick_next(s, rng)


def ends_at(s, now, rng=random):
    """absolute time `s` ends, `math.inf` if it never does"""
    d = duration(s)
    return now + rng.uniform(*d) if d else math.inf
