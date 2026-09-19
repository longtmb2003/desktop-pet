import pytest

from mochi import physics
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
from mochi.state import Action, Expression  # noqa: E402


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


# ---- shaking ----------------------------------------------------------------------------------------------
def held_and_moved(pet, monkeypatch):
    """press on the pet and start dragging it; returns the mouse-event factory"""
    import mochi.pet as mp
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    monkeypatch.setattr(mp.time, "monotonic", lambda: 50.0)

    def ev(kind, x, y):
        return QMouseEvent(kind, QPointF(x, y), QPointF(x, y), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    pet.mousePressEvent(ev(QEvent.MouseButtonPress, 100, 100))
    return (lambda x, y: pet.mouseMoveEvent(ev(QEvent.MouseMove, x, y)),
            lambda x, y: pet.mouseReleaseEvent(ev(QEvent.MouseButtonRelease, x, y)))


def test_a_shake_makes_the_held_pet_dizzy_and_it_stays_dizzy_after_the_release(pet, monkeypatch):
    move, release = held_and_moved(pet, monkeypatch)
    monkeypatch.setattr("mochi.pet.physics.is_shake", lambda trail, now: True)
    move(140, 100)
    assert pet.state == State(Motion.DRAG, Expression.DIZZY) and pet.shaken
    release(140, 100)
    assert pet.state == State(Motion.AIRBORNE, Expression.DIZZY)
    run_until(pet, lambda: pet.state.motion is Motion.WALK)
    assert pet.state.expression is Expression.DIZZY                    # gets up staggering
    run_until(pet, lambda: pet.state.expression is Expression.NORMAL)


def test_a_normal_drag_and_release_is_not_dizzy(pet, monkeypatch):
    move, release = held_and_moved(pet, monkeypatch)
    move(140, 100); move(180, 100)
    release(180, 100)
    assert pet.state == State(Motion.AIRBORNE) and not pet.shaken


def test_the_shake_reaction_fires_once_per_drag(pet, monkeypatch):
    calls = []
    move, release = held_and_moved(pet, monkeypatch)
    monkeypatch.setattr("mochi.pet.physics.is_shake", lambda trail, now: calls.append(1) or True)
    move(140, 100); move(100, 100); move(140, 100)
    assert len(calls) == 1                                              # no re-triggering while already shaken
    release(140, 100)
    held_and_moved(pet, monkeypatch)                                    # pick it up again: reset
    assert pet.shaken is False


# ---- click vs double-click ------------------------------------------------------------------------------------
def click_events(pet, monkeypatch):
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    monkeypatch.setattr("mochi.pet.time.monotonic", lambda: 50.0)

    def ev(kind):
        return QMouseEvent(kind, QPointF(100, 100), QPointF(100, 100), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    press = lambda: pet.mousePressEvent(ev(QEvent.MouseButtonPress))                         # noqa: E731
    release = lambda: pet.mouseReleaseEvent(ev(QEvent.MouseButtonRelease))                   # noqa: E731
    double = lambda: pet.mouseDoubleClickEvent(ev(QEvent.MouseButtonDblClick))               # noqa: E731
    return press, release, double


def on_the_floor(pet):
    pet.px, pet.py, pet.vy, pet.vx, pet.support = 300, floor_y(pet), 0.0, 0.0, None
    pet.enter(State(Motion.AIRBORNE)); run_until(pet, lambda: pet.state.motion is Motion.IDLE)


def test_a_single_click_pets_only_after_the_double_click_delay(pet, monkeypatch):
    on_the_floor(pet)
    press, release, _ = click_events(pet, monkeypatch)
    press(); release()
    assert pet.state.expression is Expression.NORMAL and pet.click_timer.isActive()   # still waiting for a second click
    pet.click_timer.timeout.emit()
    assert pet.state.expression is Expression.HAPPY and pet.hearts and pet.vy < 0


def test_a_double_click_flips_and_never_pets(pet, monkeypatch):
    on_the_floor(pet)
    press, release, double = click_events(pet, monkeypatch)
    press(); release(); double(); release()
    assert not pet.click_timer.isActive()                                   # the first click's pet was cancelled
    assert pet.state == State(action=Action.FLIP) and pet.vy < 0 and not pet.hearts
    seen = set()
    run_until(pet, lambda: seen.add(pet.state.expression) or pet.state.action is not Action.FLIP)
    assert seen == {Expression.NORMAL}                                      # never happy: no flip + happy double reaction
    run_until(pet, lambda: pet.grounded, frames=5)                          # touches down within a few frames of the end
    assert pet.py == floor_y(pet)


def test_the_flip_lands_when_it_ends_and_clicks_during_it_are_ignored(pet, monkeypatch):
    on_the_floor(pet)
    press, release, double = click_events(pet, monkeypatch)
    double()
    pet.tick(); pet.tick()
    press(); release(); pet.click_timer.timeout.emit()
    assert pet.state.action is Action.FLIP                                  # a click mid-flip does not interrupt it
    n = 0
    while pet.state.action is Action.FLIP and n < 100: pet.tick(); n += 1
    assert 15 <= n <= 18                                                    # 0.55 s at 33 ms/frame, minus the two ticks above
    assert pet.py >= floor_y(pet) - 15                                      # back on the ground as the flip ends, not still in the air


def test_a_double_click_on_an_airborne_pet_does_nothing(pet, monkeypatch):
    _, _, double = click_events(pet, monkeypatch)
    pet.enter(State(Motion.AIRBORNE)); pet.grounded = False
    double()
    assert pet.state == State(Motion.AIRBORNE)


def test_a_delayed_pet_is_dropped_if_the_pet_is_being_dragged_by_then(pet, monkeypatch):
    on_the_floor(pet)
    press, release, _ = click_events(pet, monkeypatch)
    press(); release(); press()                                             # second press starts a new interaction
    pet.click_timer.timeout.emit()
    assert pet.state.expression is Expression.NORMAL


def test_every_visible_pixel_of_a_flipping_pet_is_clickable_and_inside_the_window(pet):
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QImage, QPainter
    pet.grounded = False
    for facing in (1, -1):
        for k in range(12):
            pet.facing, pet.state, pet.dur, pet.began, pet.t = facing, State(action=Action.FLIP), 0.55, 10.0, 10.0 + 0.55 * k / 11
            pet.mask_key = None; pet.update_mask(); m = pet.mask(); pet.clearMask()      # render() would clip to the mask: draw unmasked
            img = QImage(S, S, QImage.Format_ARGB32); img.fill(0)
            pt = QPainter(img); pet.render(pt, QPoint(0, 0)); pt.end()
            for y in range(S):
                for x in range(S):
                    if img.pixel(x, y) >> 24 > 40:
                        assert m.contains(QPoint(x, y)), (facing, k, x, y)
                        assert 0 < x < S - 1 and 0 < y < S - 1, ("clipped by the window edge", facing, k, x, y)


# ---- losing the ground ----------------------------------------------------------------------------------------
def standing_on_a_window(pet, height=300, motion=Motion.IDLE):
    g = pet.screen_geo()
    top = g.top + height
    pet.wins = {"w": (g.left + 100, top, 500, 200)}
    pet.px, pet.py, pet.vy, pet.vx, pet.support = g.left + 250, top - FEET, 0.0, 0.0, "w"
    pet.enter(State(motion)); pet.tick()
    assert pet.support == "w" and pet.grounded


def test_the_window_vanishing_scares_the_pet_and_it_falls_at_once(pet):
    standing_on_a_window(pet)
    pet.set_windows({})
    pet.tick()
    assert pet.state == State(Motion.AIRBORNE, Expression.SCARED) and not pet.grounded and pet.support is None
    assert pet.vy > 0 and pet.vx == 0                                   # falls straight down, immediately
    run_until(pet, lambda: pet.state.motion is not Motion.AIRBORNE)
    assert pet.state == State() and pet.py == floor_y(pet)              # a normal fall: lands calmly, no lasting fear


@pytest.mark.parametrize("motion", [Motion.WALK, Motion.SLEEP])
def test_a_walking_or_sleeping_pet_is_scared_too(pet, motion):
    standing_on_a_window(pet, motion=motion)
    pet.set_windows({})
    pet.tick()
    assert pet.state == State(Motion.AIRBORNE, Expression.SCARED)


def test_a_high_fall_can_still_end_dizzy(pet, monkeypatch):
    standing_on_a_window(pet)
    monkeypatch.setattr("mochi.pet.IMPACT_DIZZY", 500)                  # make this fall count as a hard landing
    pet.set_windows({})
    run_until(pet, lambda: pet.state.motion is Motion.WALK)
    assert pet.state.expression is Expression.DIZZY


def test_a_window_that_is_merely_out_from_under_the_pet_does_not_scare_it(pet):
    standing_on_a_window(pet)
    g = pet.screen_geo()
    pet.set_windows({"w": (g.left + 900, g.top + 300, 500, 200)})       # the window moved sideways, it still exists
    seen = set()
    run_until(pet, lambda: seen.add(pet.state.expression) or pet.grounded)
    assert Expression.SCARED not in seen and pet.support is None       # it simply walks off the edge and falls


def test_a_click_hop_off_a_window_is_not_scary(pet):
    standing_on_a_window(pet)
    pet.vy = -420; pet.enter(State(expression=Expression.HAPPY))        # what pet_it() does
    pet.tick()
    assert pet.state.expression is Expression.HAPPY


def test_the_floor_never_scares_and_a_dropped_pet_is_not_scared(pet):
    pet.px, pet.py, pet.vy, pet.vx, pet.support = 300, floor_y(pet) - 200, 0.0, 0.0, None
    pet.enter(State(Motion.AIRBORNE))
    seen = set()
    run_until(pet, lambda: seen.add(pet.state.expression) or pet.state.motion is not Motion.AIRBORNE)
    assert Expression.SCARED not in seen


def test_the_scared_pet_paints_inside_its_mask_and_differs_from_a_calm_fall(pet):
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QImage, QPainter

    def frame(state):
        pet.state, pet.grounded, pet.t, pet.began, pet.dur = state, False, 10.3, 10.0, 1.0
        pet.mask_key = None; pet.update_mask(); m = pet.mask(); pet.clearMask()
        img = QImage(S, S, QImage.Format_ARGB32); img.fill(0)
        pt = QPainter(img); pet.render(pt, QPoint(0, 0)); pt.end()
        return img, m
    scared, m = frame(State(Motion.AIRBORNE, Expression.SCARED))
    calm, _ = frame(State(Motion.AIRBORNE))
    assert scared != calm
    assert all(m.contains(QPoint(x, y)) for y in range(S) for x in range(S) if scared.pixel(x, y) >> 24 > 40)
    assert not any(scared.pixel(x, y) >> 24 for x in range(S) for y in (S - 1,))          # pedalling legs stay inside the window


# ---- pushing against an edge ----------------------------------------------------------------------------------
def pushing_setup(pet, monkeypatch, roll):
    import mochi.pet as mp
    dizzy_on_a_window(pet)
    pet.enter(State(Motion.WALK))
    pet.facing = 1
    monkeypatch.setattr(mp.random, "random", lambda: roll)
    monkeypatch.setattr(mp.random, "choice", lambda seq: seq[-1] if seq[0] == -1 else seq[0])   # random facing: towards the edge; else WALK


def test_a_walker_can_push_against_the_edge_then_turn_round(pet, monkeypatch):
    pushing_setup(pet, monkeypatch, 0.45)                                # not a hop (>= 0.4), but a push (< PUSH_CHANCE)
    run_until(pet, lambda: pet.state.action is Action.PUSH)
    g = pet.screen_geo()
    edge_x = pet.px
    assert pet.state == State(Motion.WALK, action=Action.PUSH) and pet.facing == 1 and pet.support == "w"
    lo, hi = physics.span(pet.wins, g, "w")
    assert pet.px + S / 2 == hi                                              # stopped exactly at the edge, not past it
    for _ in range(10):
        pet.tick()
        assert pet.px == edge_x and pet.state.action is Action.PUSH      # it stands still and shoves
    run_until(pet, lambda: pet.state.action is not Action.PUSH)
    assert pet.state == State(Motion.WALK) and pet.facing == -1          # then heads back the way it came
    pet.tick()
    assert pet.px < edge_x


def test_no_push_when_the_roll_says_turn(pet, monkeypatch):
    pushing_setup(pet, monkeypatch, 0.9)
    seen = set()
    run_until(pet, lambda: seen.add(pet.facing) or pet.facing == -1)
    assert pet.state == State(Motion.WALK)


def test_a_dizzy_pet_never_pushes(pet, monkeypatch):
    pushing_setup(pet, monkeypatch, 0.45)
    pet.enter(State(Motion.WALK, Expression.DIZZY))
    for _ in range(120):
        pet.tick()
        assert pet.state.action is not Action.PUSH


@pytest.mark.parametrize("facing", [1, -1])
def test_the_pushing_pet_paints_inside_its_mask(pet, facing):
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QImage, QPainter
    pet.grounded, pet.facing, pet.state = True, facing, State(Motion.WALK, action=Action.PUSH)
    for k in range(8):
        pet.t, pet.began, pet.dur = 10.0 + k * 0.05, 10.0, 1.5
        pet.mask_key = None; pet.update_mask(); m = pet.mask(); pet.clearMask()
        img = QImage(S, S, QImage.Format_ARGB32); img.fill(0)
        pt = QPainter(img); pet.render(pt, QPoint(0, 0)); pt.end()
        for y in range(S):
            for x in range(S):
                if img.pixel(x, y) >> 24 > 40:
                    assert m.contains(QPoint(x, y)), (facing, k, x, y)


# ---- speech bubble ---------------------------------------------------------------------------------------------
def test_losing_the_ground_makes_the_pet_yell(pet):
    standing_on_a_window(pet)
    pet.set_windows({})
    pet.tick()
    assert pet.bubble.isVisible() and pet.bubble.lines == "Á!"
    assert (pet.width(), pet.height()) == (S, S)                        # the bubble never enlarges the pet window


def test_chatter_is_suppressed_by_quiet_mode_and_by_its_own_switch_but_urgent_speech_is_not(pet):
    pet.cfg.quiet = True
    pet.say("lảm nhảm", chatter=True); assert not pet.bubble.isVisible()
    pet.say("Á!", urgent=True); assert pet.bubble.isVisible()          # quiet only silences unprompted talk
    pet.bubble.dismiss()
    pet.cfg.quiet, pet.cfg.chatter = False, False
    pet.say("lảm nhảm", chatter=True); assert not pet.bubble.isVisible()
    pet.cfg.chatter = True
    pet.say("lảm nhảm", chatter=True); assert pet.bubble.isVisible()


def test_a_fullscreen_app_means_quiet_unless_that_is_switched_off(pet):
    assert not pet.quiet
    pet.fullscreen = True
    assert pet.quiet
    pet.cfg.quiet_auto = False
    assert not pet.quiet
    pet.cfg.quiet = True
    assert pet.quiet


def test_the_bubble_follows_the_pet_and_stays_on_screen(pet):
    pet.say("xin chào", urgent=True)
    g = pet.screen_geo()
    for px in (g.left - 50, g.left + 400, g.right - 20):
        pet.px, pet.py = px, g.top + 200
        pet.tick()
        b = pet.bubble
        assert g.left <= b.x() and b.x() + b.width() <= g.right + 1


def test_a_random_remark_turns_up_now_and_then_when_idle(pet, monkeypatch):
    pet.enter(State()); pet.next_chat = 0.0
    monkeypatch.setattr("mochi.pet.random.choice", lambda seq: seq[0])
    pet.tick()
    assert pet.bubble.isVisible() and pet.next_chat > pet.t + 100       # and the next one is minutes away, not seconds


# ---- pomodoro --------------------------------------------------------------------------------------------------
class Clock:
    def __init__(self): self.t = 1000.0
    def __call__(self): return self.t


def pomodoro_pet(pet, monkeypatch):
    import mochi.pet as mp
    chimes = []
    monkeypatch.setattr(mp, "chime", lambda: chimes.append(1))
    clock = Clock(); pet.pomo.clock = clock
    on_the_floor(pet)
    return clock, chimes


def test_focus_puts_the_pet_at_its_laptop_and_keeps_it_there(pet, monkeypatch):
    clock, _ = pomodoro_pet(pet, monkeypatch)
    pet.start_focus(25)
    assert pet.state == State(action=Action.WORK) and pet.pomo.focusing and pet.bubble.lines == "Tập trung nào! 25 phút"
    for _ in range(int(40 / 0.033)):                                     # 40 s: several WORK timeouts, never wandering off
        pet.tick()
        assert pet.state.action is Action.WORK


def test_pausing_or_resetting_lets_the_pet_go_back_to_normal_life(pet, monkeypatch):
    clock, _ = pomodoro_pet(pet, monkeypatch)
    pet.start_focus(25); pet.pomo.pause()
    run_until(pet, lambda: pet.state.action is not Action.WORK)
    assert not pet.pomo.focusing


def test_the_end_of_focus_announces_chimes_and_starts_the_break(pet, monkeypatch):
    clock, chimes = pomodoro_pet(pet, monkeypatch)
    pet.start_focus(1)
    pet.bubble.dismiss()
    clock.t += 61; pet.tick()
    assert pet.pomo.phase == "break" and "Hết giờ tập trung" in pet.bubble.lines and chimes == [1]
    assert pet.state.expression is Expression.HAPPY
    clock.t += 400; pet.tick()
    assert not pet.pomo.active and chimes == [1, 1]
    assert pet.state.action is not Action.WORK                           # no laptop during the break or afterwards


def test_no_chime_in_quiet_mode_or_with_sound_off_but_the_bubble_still_shows(pet, monkeypatch):
    clock, chimes = pomodoro_pet(pet, monkeypatch)
    pet.cfg.quiet = True
    pet.start_focus(1); pet.bubble.dismiss(); clock.t += 61; pet.tick()
    assert chimes == [] and "Hết giờ" in pet.bubble.lines               # explicit user-requested notice is still shown
    pet.cfg.quiet, pet.cfg.sound = False, False
    pet.bubble.dismiss(); pet.pomo.reset(); pet.start_focus(1); clock.t += 61; pet.tick()
    assert chimes == []


def test_starting_focus_while_airborne_does_not_freeze_the_fall(pet, monkeypatch):
    pomodoro_pet(pet, monkeypatch)
    pet.enter(State(Motion.AIRBORNE)); pet.grounded = False
    pet.start_focus(25)
    assert pet.state == State(Motion.AIRBORNE)
    run_until(pet, lambda: pet.state.motion is not Motion.AIRBORNE)
    assert pet.pomo.focusing


def test_the_laptop_pose_paints_inside_its_mask(pet):
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QImage, QPainter
    pet.grounded, pet.state = True, State(action=Action.WORK)
    for facing in (1, -1):
        pet.facing = facing
        for k in range(6):
            pet.t, pet.began, pet.dur = 10 + k * 0.07, 10.0, 8.0
            pet.mask_key = None; pet.update_mask(); m = pet.mask(); pet.clearMask()
            img = QImage(S, S, QImage.Format_ARGB32); img.fill(0)
            pt = QPainter(img); pet.render(pt, QPoint(0, 0)); pt.end()
            assert all(m.contains(QPoint(x, y)) for y in range(S) for x in range(S) if img.pixel(x, y) >> 24 > 40)


# ---- settings that change behaviour ----------------------------------------------------------------------------
def test_time_of_day_is_read_from_the_local_clock_unless_off_or_being_handled(pet):
    pet.now_hour = lambda: 3
    pet.t = 1000.0
    assert pet.hour() == 3
    pet.last_touch = pet.t - 5                                       # just played with: never nudged to sleep
    assert pet.hour() is None
    pet.last_touch = -1e9; pet.cfg.time_of_day = False
    assert pet.hour() is None


def test_the_pet_reads_the_clock_through_datetime_now(pet):
    from datetime import time
    assert pet.now_hour() == 15 and pet.now_time() == time(15, 0)                  # (the tests' fixed afternoon; local time when real)


def test_speed_setting_scales_the_walk(pet):
    def walked(speed):
        pet.cfg.speed = speed
        on_the_floor(pet); pet.enter(State(Motion.WALK)); pet.facing = 1
        g = pet.screen_geo(); pet.px = g.left + 400; x0 = pet.px
        for _ in range(10): pet.tick()
        return pet.px - x0
    slow, fast = walked(1.0), walked(2.0)
    assert fast == pytest.approx(2 * slow, rel=0.05)


def test_chase_switch_reaches_the_behaviour_picker(pet, monkeypatch):
    seen = {}
    import mochi.pet as mp
    monkeypatch.setattr(mp, "after", lambda s, **kw: seen.update(kw) or State())
    pet.cfg.chase = False
    on_the_floor(pet); pet.enter(State()); pet.until = 0.0; pet.tick()
    assert seen["chase"] is False and "hour" in seen


# ---- cpu monitor and frame rate --------------------------------------------------------------------------------
def test_a_busy_cpu_makes_the_pet_hot_with_hysteresis_and_one_remark(pet):
    readings = iter([50, 85, 90, 70, 60])
    pet.read_cpu = lambda: next(readings)
    seen = []
    for _ in range(5):
        pet.poll_cpu(); seen.append(pet.hot)
        if pet.hot: pet.bubble.dismiss()
    assert seen == [False, True, True, True, False]                      # 70% is inside the dead band: still hot
    pet.hot = False; pet.bubble.dismiss()
    pet.read_cpu = lambda: 95
    pet.poll_cpu(); assert pet.bubble.lines == "Máy nóng quá..."


def test_no_remark_when_quiet_and_a_missing_psutil_changes_nothing(pet):
    pet.cfg.quiet = True
    pet.read_cpu = lambda: 99
    pet.poll_cpu(); assert pet.hot and not pet.bubble.isVisible()
    pet.hot = False; pet.read_cpu = lambda: None                         # psutil not installed
    pet.poll_cpu(); assert not pet.hot


def test_the_monitor_timer_follows_the_setting_and_availability(pet, monkeypatch):
    import mochi.pet as mp
    monkeypatch.setattr(mp.monitor, "AVAILABLE", True)
    pet.read_cpu = lambda: 0.0
    pet.cfg.monitor = True; pet.sync_monitor(); assert pet.mon_timer.isActive() and pet.mon_timer.interval() == 8000
    pet.hot = True
    pet.cfg.monitor = False; pet.sync_monitor(); assert not pet.mon_timer.isActive() and not pet.hot
    monkeypatch.setattr(mp.monitor, "AVAILABLE", False)
    pet.cfg.monitor = True; pet.sync_monitor(); assert not pet.mon_timer.isActive()


def test_frame_rate_drops_only_when_resting_and_never_during_physics(pet):
    def fps_ms(state, **kw):
        for k, v in kw.items(): setattr(pet, k, v)
        pet.state = state; pet.retune(); return pet.timer.interval()
    assert fps_ms(State(), grounded=True, hot=False) == 33
    assert fps_ms(State(Motion.SLEEP)) == 50                             # asleep: 20 fps is plenty for the zzz
    assert fps_ms(State(), hot=True) == 50                               # resting on a busy CPU
    assert fps_ms(State(Motion.AIRBORNE), grounded=False) == 33          # falling: full rate, or the steps get coarse
    assert fps_ms(State(Motion.DRAG)) == 33
    assert fps_ms(State(action=Action.FLIP), grounded=True) == 33        # a one-shot animation
    pet.hot = False; pet.cfg.quiet = True
    assert fps_ms(State(Motion.WALK), grounded=True) == 50               # quiet mode also rests it
    pet.cfg.quiet = False
    assert fps_ms(State(Motion.WALK), grounded=True) == 33


def test_a_hot_pet_walks_slower(pet):
    def walked(hot):
        pet.hot = hot
        on_the_floor(pet); pet.enter(State(Motion.WALK)); pet.facing = 1
        g = pet.screen_geo(); pet.px = g.left + 400; x0 = pet.px
        for _ in range(10): pet.tick()
        return pet.px - x0
    assert walked(True) == pytest.approx(0.6 * walked(False), rel=0.05)


def test_the_tired_pet_paints_inside_its_mask_and_looks_different(pet):
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QImage, QPainter

    def frame(hot):
        pet.hot, pet.grounded, pet.state, pet.t = hot, True, State(), 10.4
        pet.mask_key = None; pet.update_mask(); m = pet.mask(); pet.clearMask()
        img = QImage(S, S, QImage.Format_ARGB32); img.fill(0)
        pt = QPainter(img); pet.render(pt, QPoint(0, 0)); pt.end()
        return img, m
    tired, m = frame(True)
    assert tired != frame(False)[0]
    assert all(m.contains(QPoint(x, y)) for y in range(S) for x in range(S) if tired.pixel(x, y) >> 24 > 40)
