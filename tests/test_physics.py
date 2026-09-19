import pytest

from mochi.physics import FEET, GRAVITY, HEAD, Bounds, covered, hop_target, span, surface

B = Bounds(0, 0, 1919, 1079)
FLOOR = 1080 - FEET


def test_floor_when_no_windows():
    assert surface({}, None, 500, 900, B) == (FLOOR, None)


def test_stands_on_a_window_below_the_feet():
    wins = {"a": (100, 700, 600, 300)}
    assert surface(wins, None, 400, 500, B) == (700 - FEET, "a")


def test_ignores_a_window_above_the_feet():
    assert surface({"a": (100, 300, 600, 300)}, None, 400, 900, B) == (FLOOR, None)


def test_keeps_the_window_it_already_stands_on():
    wins = {"a": (100, 700, 600, 300)}
    assert surface(wins, "a", 400, 720, B)[1] == "a"         # feet a little below the top edge: still riding
    assert surface(wins, None, 400, 720, B)[1] is None


def test_too_narrow_window_is_not_a_surface():
    assert surface({"a": (100, 700, 40, 300)}, None, 120, 500, B)[1] is None


def test_window_too_close_to_the_screen_top_is_ignored():
    assert surface({"a": (100, HEAD - 1, 600, 300)}, None, 400, 100, B)[1] is None


def test_centre_outside_the_window_x_range():
    assert surface({"a": (100, 700, 600, 300)}, None, 900, 500, B)[1] is None


def test_picks_the_highest_visible_surface():
    wins = {"low": (0, 800, 900, 200), "high": (0, 500, 900, 200)}
    assert surface(wins, None, 400, 100, B)[1] == "high"


def test_covered_by_a_window_stacked_above():
    wins = {"a": (100, 500, 800, 400), "b": (100, 480, 800, 500)}       # b is above a and overlaps its top edge
    assert covered(wins, "a", 400, 501) and not covered(wins, "b", 400, 481)
    assert surface(wins, None, 400, 300, B)[1] == "b"


def test_stacking_order_matters():
    a, h = (100, 500, 800, 400), (100, 400, 800, 200)
    assert surface({"a": a, "h": h}, None, 400, 300, B)[1] == "h"       # h above a hides a's top edge
    assert surface({"h": h, "a": a}, None, 400, 300, B)[1] == "h"       # h is higher anyway, and a is not hidden


def test_riding_window_that_gets_covered_is_dropped():
    wins = {"a": (100, 500, 800, 400), "c": (100, 495, 800, 300)}
    assert surface(wins, "a", 400, 494, B)[1] != "a"


def test_span():
    assert span({}, B, None) == (50, 1869)
    assert span({"a": (300, 700, 400, 300)}, B, "a") == (334, 666)


def test_hop_lands_on_the_target_window():
    cx, feet = 500, 1080                                                  # standing on the floor
    wins = {"a": (600, 900, 400, 300)}                                    # window top is 180 px up: reachable
    vx, vy, face = hop_target(wins, cx, feet, B)
    assert vy < 0 and face == 1
    t = (-vy + (vy * vy - 2 * GRAVITY * (feet - 900)) ** .5) / GRAVITY    # when the feet come back down to the window top
    assert cx + vx * t == pytest.approx(600 + 40)                         # aims 40 px inside the window's left edge


def test_hop_keeps_facing_when_already_above_the_target():
    assert hop_target({"a": (400, 900, 400, 300)}, 500, 1080, B)[2] is None


def test_hop_ignores_windows_out_of_reach():
    assert hop_target({"a": (600, 500, 400, 300)}, 500, 1080, B) is None                  # 580 px up


def test_hop_skips_a_landing_spot_hidden_by_another_window():
    a, b = (600, 900, 400, 300), (500, 850, 600, 300)
    assert hop_target({"a": a, "b": b}, 500, 1080, B) is None                             # b is above a and covers the spot
    assert hop_target({"b": b, "a": a}, 500, 1080, B) is not None                         # a is above b: a is free


def test_window_narrower_than_min_width_is_not_a_surface_or_hop_target():
    from mochi.physics import MIN_W
    narrow = {"a": (400, 900, MIN_W - 1, 300)}
    assert surface(narrow, None, 400 + MIN_W // 2, 500, B)[1] is None
    assert hop_target(narrow, 400, 1080, B) is None
    wide = {"a": (400, 900, MIN_W, 300)}
    assert surface(wide, None, 400 + MIN_W // 2, 500, B)[1] == "a"


def test_walking_range_is_never_empty_on_a_valid_surface():
    from mochi.physics import MIN_W
    lo, hi = span({"a": (400, 900, MIN_W, 300)}, B, "a")
    assert lo <= hi


# ---- throwing ---------------------------------------------------------------------------------------------
import math  # noqa: E402

from mochi.physics import (  # noqa: E402
    BOUNCE_X, HEAD_ROOM, S, TERMINAL, THROW_MAX, THROW_MIN, VEL_WINDOW, WALL_PAD, DragTracker, step_air,
)


def drag(*pts):
    d = DragTracker()
    for p in pts: d.add(*p)
    return d


def test_velocity_of_a_steady_drag():
    d = drag((0.00, 0, 0), (0.02, 20, 0), (0.04, 40, 0), (0.06, 60, 0))          # 1000 px/s to the right
    vx, vy = d.velocity(0.06)
    assert vx == pytest.approx(1000) and vy == pytest.approx(0)


def test_velocity_is_zero_if_the_mouse_stopped_before_release():
    d = drag((0.0, 0, 0), (0.02, 20, 0), (0.04, 40, 0))
    assert d.velocity(0.04 + VEL_WINDOW + 0.01) == (0.0, 0.0)               # held still, then let go: a drop, not a throw


def test_velocity_needs_two_recent_samples():
    assert drag().velocity(1.0) == (0.0, 0.0)
    assert drag((1.0, 5, 5)).velocity(1.0) == (0.0, 0.0)


def test_old_samples_do_not_count():
    d = drag((0.0, 0, 0), (0.01, 500, 0), (1.00, 500, 0), (1.02, 500, 0))    # a fast move a second ago, then still
    assert d.velocity(1.02)[0] == pytest.approx(0)


def test_recent_movement_weighs_more():
    slow_then_fast = drag((0.00, 0, 0), (0.05, 5, 0), (0.10, 105, 0))       # 100 px/s then 2000 px/s
    vx = slow_then_fast.velocity(0.10)[0]
    assert (100 + 2000) / 2 < vx < 2000


def test_velocity_is_clamped_keeping_direction():
    vx, vy = drag((0.0, 0, 0), (0.01, 300, 400)).velocity(0.01)              # 50000 px/s
    assert math.hypot(vx, vy) == pytest.approx(THROW_MAX) and vy / vx == pytest.approx(4 / 3)


def test_keeps_only_the_last_eight_samples():
    d = drag(*[(i * 0.001, i, 0) for i in range(30)])
    assert len(d.samples) == 8


def test_reset_forgets_everything():
    d = drag((0.0, 0, 0), (0.01, 50, 0)); d.reset()
    assert d.velocity(0.01) == (0.0, 0.0)


# ---- flight ---------------------------------------------------------------------------------------------------
FLOOR_Y = 900.0


def fly(x, y, vx, vy, floor=FLOOR_Y, seconds=30.0, dt=1 / 60):
    """simulate until landed; returns (trajectory of Flights, time)"""
    out, t = [], 0.0
    while t < seconds:
        f = step_air(x, y, vx, vy, dt, floor, B)
        out.append(f); x, y, vx, vy = f.x, f.y, f.vx, f.vy; t += dt
        if f.landed: break
    return out, t


def test_gravity_pulls_down():
    f = step_air(500, 100, 0, 0, 1 / 60, FLOOR_Y, B)
    assert f.vy > 0 and f.y > 100 and not f.landed and not f.hit and f.impact == 0


def test_gravity_never_exceeds_terminal_speed_but_a_faster_throw_is_kept():
    assert step_air(500, 0, 0, TERMINAL, 1 / 60, 5000, B).vy == TERMINAL
    assert step_air(500, 0, 0, TERMINAL + 800, 1 / 60, 5000, B).vy == TERMINAL + 800


def test_wall_bounce_loses_energy_and_flips_direction():
    lo = B.left - WALL_PAD
    f = step_air(lo + 1, 300, -1000, 0, 1 / 60, FLOOR_Y, B)
    assert f.hit and f.x == lo and f.vx == pytest.approx(1000 * BOUNCE_X) and f.impact == pytest.approx(1000)
    hi = B.right - S + WALL_PAD
    assert step_air(hi - 1, 300, 1000, 0, 1 / 60, FLOOR_Y, B).vx < 0


def test_moving_away_from_the_wall_does_not_re_bounce():
    lo = B.left - WALL_PAD
    f = step_air(lo - 5, 300, 200, 0, 1 / 60, FLOOR_Y, B)                  # already beyond it but heading back in
    assert not f.hit and f.vx == 200


def test_ceiling_bounce():
    ceiling = B.top - HEAD_ROOM
    f = step_air(500, ceiling + 2, 0, -1500, 1 / 60, FLOOR_Y, B)
    assert f.hit and f.y == ceiling and f.vy > 0 and f.impact > 1000


def test_floor_bounce_then_rest():
    f = step_air(500, FLOOR_Y - 1, 300, 1200, 1 / 60, FLOOR_Y, B)
    assert f.hit and not f.landed and f.y == FLOOR_Y and f.vy < 0 and 0 < f.vx < 300
    f = step_air(500, FLOOR_Y - 1, 300, 200, 1 / 60, FLOOR_Y, B)          # too slow to bounce: settles
    assert f.landed and (f.y, f.vx, f.vy) == (FLOOR_Y, 0.0, 0.0)


@pytest.mark.parametrize("vx, vy", [(2600, -200), (-2600, 0), (0, -2600), (1800, -1800), (-2600, -2600), (0, 0)])
def test_every_throw_settles_inside_the_screen(vx, vy):
    flights, t = fly(900, 300, vx, vy)
    assert flights[-1].landed and t < 30, "never came to rest"
    assert all(B.left - WALL_PAD <= f.x <= B.right - S + WALL_PAD for f in flights)      # never leaves the screen
    assert all(f.y >= B.top - HEAD_ROOM - 1e-6 and f.y <= FLOOR_Y + 1e-6 for f in flights)


def test_no_endless_jitter_bounces_die_out():
    flights, _ = fly(900, 0, 0, 0)
    impacts = [f.impact for f in flights if f.impact]
    assert impacts == sorted(impacts, reverse=True) and len(impacts) < 8    # each floor bounce is weaker than the last


def test_a_free_fall_from_the_top_never_exceeds_terminal():
    flights, _ = fly(900, -100, 0, 0)
    assert max(f.impact for f in flights) <= TERMINAL + 1


def test_throw_threshold_constants_are_sane():
    assert 0 < THROW_MIN < THROW_MAX


def test_trail_keeps_only_the_shake_window():
    from mochi.physics import SHAKE_WINDOW
    d = DragTracker()
    for i in range(100): d.add(i * 0.05, i, 0)                          # 5 s of samples, 20 per second
    assert d.trail[0][0] >= d.trail[-1][0] - SHAKE_WINDOW and len(d.trail) <= 20
    assert len(d.samples) == 8                                          # the velocity buffer is independent
    d.reset()
    assert not d.trail and not d.samples


def test_an_ordinary_drag_is_not_a_shake():
    from mochi.physics import is_shake
    trail = [(i * 0.01, i * 10, 0) for i in range(80)]                  # 1000 px/s in one direction for 0.8 s
    assert is_shake(trail, 0.79) is False
    assert is_shake([], 0.0) is False


def _wiggle(amp, period, dur=0.8, dt=0.01, axis=0):
    """Triangle wave of amplitude `amp` px peak-to-peak and `period` s, as a trail"""
    out = []
    for i in range(int(dur / dt)):
        t = i * dt; ph = (t / period) % 1.0
        d = amp * (2 * ph if ph < 0.5 else 2 - 2 * ph)
        out.append((t, d if axis == 0 else 0, d if axis == 1 else 0))
    return out


def test_a_vigorous_back_and_forth_is_a_shake():
    from mochi.physics import is_shake
    assert is_shake(_wiggle(120, 0.2), 0.79) is True                    # 5 Hz, 120 px strokes: ~1200 px/s
    assert is_shake(_wiggle(120, 0.2, axis=1), 0.79) is True            # vertical works too


def test_tremor_and_lazy_wiggles_are_not_shakes():
    from mochi.physics import is_shake
    assert is_shake(_wiggle(15, 0.04, dt=0.005), 0.79) is False         # ~750 px/s and many reversals, but 15 px strokes
    assert is_shake(_wiggle(120, 0.8), 0.79) is False                   # big but only ~1 reversal
    assert is_shake(_wiggle(45, 0.2), 0.79) is False                    # strokes reach 40 px but 450 px/s is too slow


def test_a_single_turn_or_a_flick_is_not_a_shake():
    from mochi.physics import is_shake
    there_and_back = [(i * 0.01, (i * 30 if i < 40 else (80 - i) * 30), 0) for i in range(80)]
    assert is_shake(there_and_back, 0.79) is False                      # fast, long, but one reversal
    assert is_shake([(0.0, 0, 0)], 0.0) is False                        # a single sample
    assert is_shake([(0.5, 0, 0), (0.5, 90, 0)], 0.5) is False          # zero elapsed time
