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
