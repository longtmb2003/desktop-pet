from datetime import time
from types import SimpleNamespace

import pytest

from mochi import sleep
from mochi.sleep import in_window, parse_time, scheduled


def cfg(**over):
    base = dict(nap_on=True, nap_from="12:00", nap_to="13:30", night_on=True, night_from="22:00", night_to="06:00")
    return SimpleNamespace(**{**base, **over})


@pytest.mark.parametrize("s,default,want", [("12:00", "0:00", time(12, 0)), ("9:05", "0:00", time(9, 5)), ("23:59", "0:00", time(23, 59)),
                                            ("24:00", "07:15", time(7, 15)), ("12:60", "07:15", time(7, 15)), ("x", "07:15", time(7, 15)),
                                            ("", "07:15", time(7, 15)), (None, "07:15", time(7, 15)), ("x", "y", time(0, 0))])
def test_parse_time_falls_back_to_the_default_then_midnight(s, default, want):
    assert parse_time(s, default) == want


def test_a_window_within_a_day_includes_its_start_and_not_its_end():
    a, b = time(12, 0), time(13, 30)
    assert [in_window(time(h, m), a, b) for h, m in ((11, 59), (12, 0), (13, 29), (13, 30), (14, 0))] == [False, True, True, False, False]


def test_a_window_may_run_past_midnight():
    a, b = time(22, 0), time(6, 0)
    assert [in_window(time(h, m), a, b) for h, m in ((21, 59), (22, 0), (23, 59), (0, 0), (5, 59), (6, 0), (12, 0))] == \
        [False, True, True, True, True, False, False]


def test_an_empty_window_is_empty_not_the_whole_day():
    assert not any(in_window(time(h), time(9, 0), time(9, 0)) for h in range(24))


def test_the_default_schedule_is_a_midday_nap_and_a_night():
    c = cfg()
    want = {(11, 59): "", (12, 0): "nap", (13, 29): "nap", (13, 30): "", (15, 0): "", (21, 59): "", (22, 0): "night", (3, 0): "night",
            (6, 0): "", (6, 1): ""}
    assert {t: scheduled(time(*t), c) for t in want} == want


def test_each_window_can_be_switched_off_or_moved():
    assert scheduled(time(12, 30), cfg(nap_on=False)) == "" and scheduled(time(23, 0), cfg(night_on=False)) == ""
    c = cfg(nap_from="14:00", nap_to="15:00", night_from="23:30", night_to="07:00")
    assert scheduled(time(12, 30), c) == "" and scheduled(time(14, 30), c) == "nap" and scheduled(time(22, 30), c) == ""
    assert scheduled(time(6, 30), c) == "night"


def test_garbage_times_in_the_settings_fall_back_to_the_defaults():
    c = cfg(nap_from="oops", nap_to=None, night_from="99:99", night_to="")
    assert scheduled(time(12, 30), c) == "nap" and scheduled(time(23, 0), c) == "night"


def test_defaults_match_the_documented_schedule():
    assert sleep.DEFAULTS == {"nap_from": "12:00", "nap_to": "13:30", "night_from": "22:00", "night_to": "06:00"}
