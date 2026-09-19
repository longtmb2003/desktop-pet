import math
import random

from mochi.state import Action, Expression, Motion, State, after, duration, ends_at, pick_next

RNG = random.Random(1)


def test_axes_are_independent():
    s = State(Motion.AIRBORNE, Expression.SCARED)           # the combination the old string state could not express
    assert (s.motion, s.expression, s.action) == (Motion.AIRBORNE, Expression.SCARED, Action.NONE)
    assert s != State(Motion.AIRBORNE)


def test_pick_next_never_repeats_the_current_behaviour():
    for cur in (State(), State(Motion.WALK), State(action=Action.GROOM), State(Motion.WALK, action=Action.CHASE)):
        picks = {pick_next(cur, RNG) for _ in range(300)}
        assert (cur.motion, cur.action) not in {(p.motion, p.action) for p in picks}
        assert len(picks) > 1                                # and it does vary


def test_pick_next_covers_every_behaviour():
    picks = [pick_next(State(Motion.DRAG), RNG) for _ in range(500)]
    assert len({(s.motion, s.action) for s in picks}) == 7


def test_duration():
    assert duration(State()) == (2, 5)
    assert duration(State(Motion.SLEEP)) == (8, 20)
    assert duration(State(expression=Expression.HAPPY)) == (1.4, 1.4)
    assert duration(State(action=Action.YAWN)) == (1.8, 1.8)
    assert duration(State(Motion.WALK, action=Action.CHASE)) == (5, 9)   # the action's timer wins over WALK's
    assert duration(State(Motion.DRAG)) is None and duration(State(Motion.AIRBORNE)) is None


def test_after_happy_returns_to_idle():
    assert after(State(expression=Expression.HAPPY), RNG) == State()


def test_after_yawn_naps_or_idles():
    outs = {after(State(action=Action.YAWN), RNG) for _ in range(100)}
    assert outs == {State(Motion.SLEEP), State()}


def test_after_ordinary_state_changes_behaviour():
    for _ in range(100):
        cur = State(Motion.WALK)
        nxt = after(cur, RNG)
        assert (nxt.motion, nxt.action) != (cur.motion, cur.action) and nxt.expression is Expression.NORMAL


def test_ends_at():
    assert ends_at(State(Motion.DRAG), 5.0) == math.inf
    assert all(7.0 <= ends_at(State(), 5.0, RNG) <= 10.0 for _ in range(50))


def test_dizzy_lasts_a_few_seconds_then_returns_to_normal():
    assert duration(State(Motion.WALK, Expression.DIZZY)) == (3.5, 3.5)
    assert after(State(Motion.WALK, Expression.DIZZY), RNG) == State()


def test_airborne_and_drag_never_time_out_even_when_dizzy():
    assert duration(State(Motion.AIRBORNE, Expression.DIZZY)) is None
    assert duration(State(Motion.DRAG, Expression.DIZZY)) is None
    assert ends_at(State(Motion.AIRBORNE, Expression.DIZZY), 3.0) == math.inf
