from mochi.monitor import Hysteresis


def test_hysteresis_has_a_dead_band_so_it_does_not_flicker():
    h = Hysteresis(80, 65)
    assert [h.update(v) for v in (10, 79, 80, 81, 79, 70, 66, 65, 64, 70, 90, 80)] == \
        [False, False, False, True, True, True, True, True, False, False, True, True]


def test_a_reading_that_hovers_at_the_threshold_never_toggles_more_than_once():
    h, flips, last = Hysteresis(80, 65), 0, False
    for i in range(200):
        v = 78 + 4 * (i % 2)                                             # 78, 82, 78, 82 ...
        on = h.update(v); flips += on != last; last = on
    assert flips == 1
