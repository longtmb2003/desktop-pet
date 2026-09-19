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
