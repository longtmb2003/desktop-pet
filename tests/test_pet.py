import pytest

from mochi.physics import FEET, S
from mochi.pet import MAX_DT
from mochi.state import Motion, State


def floor_y(p):
    return p.screen_geo().bottom + 1 - FEET


def test_dt_is_clamped_after_a_stall(pet):
    pet.clock.restart = lambda: 5000                        # the app froze for 5 s
    before = pet.t
    pet.tick()
    assert pet.t - before == MAX_DT


def test_dt_uses_real_frame_time(pet):
    before = pet.t
    pet.tick()
    assert pet.t - before == 0.033


def test_falls_and_lands_on_the_floor(pet):
    g = pet.screen_geo()
    pet.px, pet.py, pet.vy, pet.vx = g.left + 200, g.top - 100, 0.0, 0.0
    pet.enter(State(Motion.AIRBORNE))
    for _ in range(600):
        pet.tick()
        if pet.state.motion is not Motion.AIRBORNE:
            break
    assert pet.state.motion is Motion.IDLE and pet.grounded and pet.py == floor_y(pet)


def test_rides_a_window_and_falls_when_it_disappears(pet):
    g = pet.screen_geo()
    top = g.top + 300
    pet.wins = {"w": (g.left + 100, top, 500, 200)}
    pet.px, pet.py, pet.vy, pet.vx, pet.support = g.left + 250, top - FEET, 0.0, 0.0, "w"
    pet.enter(State())
    pet.tick()
    assert pet.support == "w" and pet.grounded and pet.py == top - FEET
    pet.set_windows({})                                     # the window was closed / minimised
    pet.tick()
    assert not pet.grounded and pet.vy > 0                  # gravity acts immediately, no grace period
    for _ in range(600):
        pet.tick()
    assert pet.py == floor_y(pet) and pet.support is None


def test_drag_freezes_physics(pet):
    pet.enter(State(Motion.DRAG))
    pet.px = pet.py = 123
    pet.tick()
    assert (pet.px, pet.py) == (123, 123)


def test_bring_back_recovers_a_lost_pet(pet):
    pet.px, pet.py, pet.support = -9999, 99999, "w"
    pet.bring_back()
    g = pet.screen_geo()
    assert pet.support is None and pet.state.motion is Motion.AIRBORNE and g.left <= pet.px + S / 2 <= g.right


def test_mask_is_only_rebuilt_when_the_shape_changes(pet):
    pet.update_mask()
    key = pet.mask_key
    pet.update_mask()
    assert pet.mask_key is key
    pet.facing = -pet.facing
    pet.update_mask()
    assert pet.mask_key != key


def test_ensure_visible_rescues_a_pet_stranded_off_every_screen(pet):
    pet.px, pet.py, pet.support = -9999, 500, "w"
    pet.ensure_visible()
    assert pet.state.motion is Motion.AIRBORNE and pet.support is None


def test_ensure_visible_leaves_a_pet_that_is_on_screen(pet):
    g = pet.screen_geo()
    pet.px, pet.py = g.left + 100, g.top + 100
    pet.enter(State())
    pet.ensure_visible()
    assert pet.state == State() and pet.px == g.left + 100


def test_ensure_visible_does_not_interrupt_a_drag(pet):
    pet.px, pet.py = -9999, 500
    pet.enter(State(Motion.DRAG))
    pet.ensure_visible()
    assert pet.state.motion is Motion.DRAG


def test_pause_freezes_and_resume_does_not_count_the_pause(pet):
    pet.set_paused(True)
    assert pet.paused and not pet.timer.isActive()
    pet.set_paused(False)
    assert not pet.paused and pet.timer.isActive()
    pet.timer.stop()


# ---- throwing ---------------------------------------------------------------------------------------------
from mochi.physics import THROW_MIN, WALL_PAD  # noqa: E402


def in_air(pet, x, y, vx, vy):
    pet.px, pet.py, pet.vx, pet.vy, pet.support = x, y, vx, vy, None
    pet.enter(State(Motion.AIRBORNE))


def settle(pet, frames=2400):
    for i in range(frames):
        pet.tick()
        if pet.state.motion is not Motion.AIRBORNE:
            return i
    raise AssertionError("still airborne")


def test_throw_below_threshold_is_a_plain_drop(pet):
    pet.throw(THROW_MIN - 1, 0)
    assert (pet.vx, pet.vy) == (0.0, 0.0) and pet.state.motion is Motion.AIRBORNE


def test_throw_above_threshold_keeps_velocity(pet):
    pet.throw(900, -400)
    assert (pet.vx, pet.vy) == (900, -400)


def test_thrown_pet_stays_on_screen_and_settles(pet):
    g = pet.screen_geo()
    in_air(pet, g.left + 100, g.top + 100, 1200, -300)                  # a firm throw, below the dizzy threshold
    for _ in range(2400):
        pet.tick()
        assert g.left - WALL_PAD <= pet.px <= g.right - S + WALL_PAD
        if pet.state.motion is not Motion.AIRBORNE: break
    assert pet.state.motion is Motion.IDLE and pet.py == floor_y(pet) and (pet.vx, pet.vy) == (0.0, 0.0)


def test_the_hardest_throw_stays_on_screen_and_lands_dizzy(pet):
    g = pet.screen_geo()
    in_air(pet, g.left + 100, g.top + 100, 2600, -300)
    for _ in range(2400):
        pet.tick()
        assert g.left - WALL_PAD <= pet.px <= g.right - S + WALL_PAD
        if pet.state.motion is not Motion.AIRBORNE: break
    assert pet.state == State(Motion.WALK, Expression.DIZZY) and pet.py == floor_y(pet)


def test_pet_thrown_sideways_along_the_floor_still_lands(pet):
    g = pet.screen_geo()
    in_air(pet, g.left + 100, floor_y(pet), 800, 0)                # exactly on the floor: used to hang in AIRBORNE forever
    settle(pet)
    assert pet.state.motion is Motion.IDLE


def test_dropped_exactly_on_the_floor_lands(pet):
    in_air(pet, pet.screen_geo().left + 100, floor_y(pet), 0, 0)
    pet.tick()
    assert pet.state.motion is Motion.IDLE


def test_release_uses_the_drag_history(pet, monkeypatch):
    import mochi.pet as mp
    now = [100.0]
    monkeypatch.setattr(mp.time, "monotonic", lambda: now[0])
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent

    def ev(kind, x, y):
        return QMouseEvent(kind, QPointF(x, y), QPointF(x, y), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    pet.mousePressEvent(ev(QEvent.MouseButtonPress, 100, 100))
    for i in range(1, 6):                                         # 1000 px/s to the right, sampled every 20 ms
        now[0] += 0.02
        pet.mouseMoveEvent(ev(QEvent.MouseMove, 100 + 20 * i, 100))
    pet.mouseReleaseEvent(ev(QEvent.MouseButtonRelease, 200, 100))
    assert pet.state.motion is Motion.AIRBORNE and pet.vx == pytest.approx(1000) and pet.vy == pytest.approx(0)


# ---- dizzy ------------------------------------------------------------------------------------------------
from mochi.physics import IMPACT_DIZZY  # noqa: E402
from mochi.state import Expression  # noqa: E402


def run_until(pet, cond, frames=3000):
    for i in range(frames):
        pet.tick()
        if cond(): return i
    raise AssertionError("condition never met")


def test_a_hard_throw_into_a_wall_makes_the_pet_dizzy_and_it_recovers(pet):
    g = pet.screen_geo()
    in_air(pet, g.left + 300, g.top + 200, 2600, 0)
    assert IMPACT_DIZZY < 2600
    run_until(pet, lambda: pet.state.expression is Expression.DIZZY)          # hit the right wall
    assert pet.state.motion is Motion.AIRBORNE                                 # dizzy while still in the air: independent axes
    run_until(pet, lambda: pet.state.motion is Motion.WALK)                    # lands, gets up and staggers
    assert pet.state.expression is Expression.DIZZY and pet.grounded
    run_until(pet, lambda: pet.state.expression is Expression.NORMAL)
    assert pet.state == State() and pet.t > 3                                  # ~3.5 s later it is back to normal


def test_gentle_throws_and_normal_falls_do_not_make_it_dizzy(pet):
    g = pet.screen_geo()
    for vx, vy in [(0, 0), (500, -200), (900, 0), (-700, -300)]:
        in_air(pet, g.left + 300, g.top - 100, vx, vy)
        pet.enter(State(Motion.AIRBORNE))
        for _ in range(3000):
            pet.tick()
            assert pet.state.expression is Expression.NORMAL, (vx, vy)
            if pet.state.motion is not Motion.AIRBORNE: break


def test_a_fall_from_the_very_top_is_below_the_dizzy_threshold(pet):
    g = pet.screen_geo()
    in_air(pet, g.left + 300, g.top - 100, 0, 0)
    peak = 0.0
    for _ in range(3000):
        pet.tick(); peak = max(peak, pet.vy)
        if pet.state.motion is not Motion.AIRBORNE: break
    assert peak < IMPACT_DIZZY


def dizzy_on_a_window(pet):
    g = pet.screen_geo()
    top, x, w = g.top + 300, g.left + 100, 300
    pet.wins = {"w": (x, top, w, 200)}
    pet.px, pet.py, pet.support, pet.vx, pet.vy = x + w - 36 - S / 2, top - FEET, "w", 0.0, 0.0    # just inside the right edge
    pet.enter(State(Motion.WALK, Expression.DIZZY))
    pet.facing = 1


def test_dizzy_walker_turns_back_at_a_window_edge_instead_of_hopping_off(pet, monkeypatch):
    import mochi.pet as mp
    dizzy_on_a_window(pet)
    monkeypatch.setattr(mp.random, "random", lambda: 0.0)                       # would always hop for a healthy walker
    for _ in range(120):
        pet.tick()
        assert pet.support == "w" and pet.vx == 0.0, "a dizzy pet must not jump off"


def test_dizzy_sway_never_carries_the_pet_off_the_window(pet):
    """the sway is about +-6 px against a 10 px margin between the walking range and the window edge (measured: 0 falls in 600 runs)"""
    import random
    random.seed(3)
    g = pet.screen_geo()
    for _ in range(20):                                                        # many staggers, each lasting the full 3.5 s
        dizzy_on_a_window(pet)
        pet.px = g.left + 100 + random.uniform(60, 240) - S / 2                # anywhere along the window top
        for _ in range(int(3.4 / 0.033)):
            pet.tick()
            assert pet.support == "w" and pet.grounded, "staggered off the window"
