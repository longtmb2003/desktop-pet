import math
import random

from mochi.state import BEHAVIORS, Action, Expression, Motion, State, after, duration, ends_at, pick_next

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
    assert len({(s.motion, s.action) for s in picks}) == 6                          # every behaviour except sleeping
    assert all(s.motion is not Motion.SLEEP for s in picks)


def test_duration():
    assert duration(State()) == (2, 5)
    assert duration(State(Motion.SLEEP)) == (8, 20)
    assert duration(State(expression=Expression.HAPPY)) == (1.4, 1.4)
    assert duration(State(action=Action.YAWN)) == (1.8, 1.8)
    assert duration(State(Motion.WALK, action=Action.CHASE)) == (5, 9)   # the action's timer wins over WALK's
    assert duration(State(Motion.DRAG)) is None and duration(State(Motion.AIRBORNE)) is None


def test_after_happy_returns_to_idle():
    assert after(State(expression=Expression.HAPPY), RNG) == State()


def test_a_yawn_is_only_a_yawn_it_never_ends_in_a_nap():
    assert {after(State(action=Action.YAWN), RNG, hour=h) for h in (None, 3, 14, 23) for _ in range(30)} == {State()}


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


def test_push_is_a_short_one_shot_and_ends_by_turning_round_or_sitting():
    s = State(Motion.WALK, action=Action.PUSH)
    lo, hi = duration(s)
    assert 1 <= lo <= hi <= 2                                     # long enough to read as a shove, short enough not to be a stall
    ends = {after(s, random.Random(i)) for i in range(50)}
    assert ends == {State(Motion.WALK), State(Motion.IDLE)}
    assert all(pick_next(State(), RNG).action is not Action.PUSH for _ in range(200))    # only ever started by reaching an edge


def freq(hour, n=4000, chase=True, cur=None, weights=None):
    cur, rng = cur or State(Motion.WALK), random.Random(7)
    out = {}
    for _ in range(n):
        s = pick_next(cur, rng, hour=hour, chase=chase, weights=weights)
        out[(s.motion, s.action)] = out.get((s.motion, s.action), 0) + 1
    return out


def test_it_never_picks_sleep_at_any_hour_even_if_a_pet_lists_it():
    listed = dict(BEHAVIORS); listed[(Motion.SLEEP, Action.NONE)] = 50                # a character pack that asks for lots of sleep
    for h in (None, 0, 3, 12, 14, 22, 23):
        assert (Motion.SLEEP, Action.NONE) not in freq(h, weights=listed)
    only = {(Motion.SLEEP, Action.NONE): 1}
    assert pick_next(State(), random.Random(1), weights=only) == State(Motion.SLEEP)          # (a pet that does nothing else)


def test_the_evening_and_night_calm_the_chasing_and_the_day_does_not():
    day, eve, night = (freq(h, cur=State()) for h in (14, 22, 2))
    assert eve[(Motion.WALK, Action.CHASE)] < 0.5 * day[(Motion.WALK, Action.CHASE)]
    assert night[(Motion.WALK, Action.CHASE)] < 0.5 * day[(Motion.WALK, Action.CHASE)]


def test_no_hour_means_no_time_of_day_effect_and_boundaries_are_where_the_docs_say():
    from mochi.state import is_night
    assert freq(None, cur=State()) == freq(14, cur=State())                          # 14:00 is neutral too
    assert [h for h in range(24) if is_night(h)] == [0, 1, 2, 3, 4, 5, 22, 23]


def test_chase_can_be_switched_off():
    assert (Motion.WALK, Action.CHASE) not in freq(14, chase=False)
    assert all(pick_next(State(), random.Random(i), chase=False).action is not Action.CHASE for i in range(300))


def test_activity_shortens_only_the_plain_stretches():
    rng = lambda: random.Random(3)                                           # noqa: E731
    calm, busy = ends_at(State(), 0, rng(), 1.0), ends_at(State(), 0, rng(), 2.0)
    assert busy == calm / 2
    assert ends_at(State(action=Action.YAWN), 0, rng(), 3.0) == ends_at(State(action=Action.YAWN), 0, rng(), 1.0)      # reactions unchanged
    assert ends_at(State(expression=Expression.DIZZY), 0, rng(), 3.0) == 3.5
    assert ends_at(State(Motion.AIRBORNE), 0, rng(), 3.0) == math.inf
