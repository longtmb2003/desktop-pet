import pytest
from conftest import write_pack  # noqa: F401

import mochi.pet as mp
from mochi import modes
from mochi.settings_dialog import SettingsDialog
from mochi.state import Action, Expression, Motion, State


@pytest.fixture
def floor(pet):
    pet.px, pet.py, pet.vx, pet.vy, pet.support = 300.0, pet.screen_geo().bottom + 1 - pet.feet, 0.0, 0.0, None      # standing on the floor
    pet.grounded = True; pet.enter(State()); pet.until = float("inf"); pet.t = 100.0; pet.last_touch = -1e9
    return pet


def values(p):
    return {k: getattr(p.cfg, k) for k in modes.KEYS}


def test_switching_mode_applies_all_its_settings_and_says_so(floor):
    assert floor.set_mode("play")
    assert values(floor) == modes.BUILTIN["play"].values and floor.cfg.mode == "play" and floor.mode().id == "play"
    assert floor.bubble.lines == "Chế độ: Chơi đùa"
    assert floor.set_mode("normal") and values(floor) == modes.DEFAULTS        # nothing of the previous mode leaks through


def test_a_mode_can_be_found_by_id_or_name_in_any_case_and_unknown_ones_change_nothing(floor):
    assert floor.set_mode("Làm việc") and floor.cfg.mode == "work"
    assert floor.set_mode("YÊN LẶNG") and floor.cfg.mode == "quiet" and floor.quiet
    before = values(floor)
    assert floor.set_mode("nope") is False and floor.set_mode("") is False and values(floor) == before


def test_sleep_mode_puts_it_to_sleep_and_keeps_it_there(floor):
    floor.set_mode("sleep")
    assert floor.state == State(Motion.SLEEP)
    for _ in range(4):                                                           # every time the sleep runs out it goes back to sleep
        floor.until = 0.0; floor.tick()
        assert floor.state == State(Motion.SLEEP)


def test_it_does_not_go_straight_back_to_sleep_after_being_played_with(floor):
    floor.set_mode("sleep")
    floor.t = 200.0; floor.last_touch = 195.0                                    # petted five seconds ago
    floor.enter(State(expression=Expression.HAPPY)); floor.until = 0.0; floor.tick()
    assert floor.state != State(Motion.SLEEP)                                    # five seconds after a pat: awake
    floor.t = 230.0; floor.enter(State(expression=Expression.HAPPY)); floor.until = 0.0; floor.tick()
    assert floor.state == State(Motion.SLEEP)                                    # 35 s later: asleep again


def test_work_mode_keeps_it_at_the_laptop(floor):
    floor.set_mode("work")
    assert floor.state == State(action=Action.WORK)
    for _ in range(4):
        floor.until = 0.0; floor.tick()
        assert floor.state == State(action=Action.WORK)
    floor.set_mode("normal"); floor.until = 0.0
    seen = set()
    for _ in range(60):
        floor.enter(State()); floor.until = 0.0; floor.tick(); seen.add(floor.state.action)
    assert Action.WORK not in seen                                               # leaving the mode frees it


def test_play_mode_leans_towards_chasing_and_work_mode_never_chases(floor):
    floor.now_hour = lambda: 14                                                  # midday: the evening never dampens the chasing

    import random
    random.seed(11)

    def share(mode, n=800):
        floor.set_mode(mode); chases = 0
        for _ in range(n):
            floor.enter(State()); floor.until = 0.0; floor.grounded = True; floor.py = floor.screen_geo().bottom + 1 - floor.feet
            floor.tick(); chases += floor.state.action is Action.CHASE
        return chases / n
    normal, play = share("normal"), share("play")
    assert play > 1.5 * normal and play > 0.2
    floor.set_mode("work"); floor.cfg.chase = True                               # even with chase switched back on ...
    assert floor.mode().stay == "work"                                           # ... it sits at its laptop, so nothing to chase with


def test_activity_of_a_mode_changes_how_long_it_does_things(floor):
    floor.set_mode("play"); busy = floor.cfg.activity
    floor.set_mode("sleep"); calm = floor.cfg.activity
    assert busy > 1 > calm


def test_saving_the_current_settings_as_a_mode_of_my_own(floor):
    floor.set_mode("play")
    floor.cfg.speed, floor.cfg.chatter = 1.2, False
    new = floor.save_mode("  Của tôi ")
    assert new.id == "custom:Của tôi" and floor.cfg.mode == new.id and floor.mode().values["speed"] == 1.2
    assert floor.mode().boost == {"chase": 4, "walk": 2}                         # it keeps the leaning of the mode it came from
    floor.set_mode("normal"); assert floor.cfg.speed == 1.0
    assert floor.set_mode("của tôi") and floor.cfg.speed == 1.2 and floor.cfg.chatter is False
    assert "custom:Của tôi" in modes.available(floor.cfg.custom_modes)


def test_saving_under_an_existing_name_replaces_it_and_blank_names_are_refused(floor):
    floor.cfg.speed = 1.5; floor.save_mode("A")
    floor.cfg.speed = 2.5; floor.save_mode("A")
    assert [m.name for m in modes.available(floor.cfg.custom_modes).values() if not m.builtin] == ["A"]
    assert floor.mode().values["speed"] == 2.5
    with pytest.raises(ValueError): floor.save_mode("   ")


def test_the_number_of_own_modes_is_capped(floor):
    for i in range(modes.MAX_CUSTOM): floor.save_mode(f"m{i}")
    with pytest.raises(ValueError): floor.save_mode("one too many")
    floor.save_mode("m3")                                                        # replacing an existing one is still fine


def test_deleting_my_mode_leaves_settings_alone_and_builtins_cannot_be_deleted(floor):
    floor.cfg.speed = 1.9; floor.save_mode("tạm")
    assert floor.delete_mode("custom:tạm") and floor.cfg.mode == "normal" and floor.cfg.speed == 1.9
    assert floor.delete_mode("custom:tạm") is False and floor.delete_mode("play") is False
    assert "play" in modes.available(floor.cfg.custom_modes)


def test_a_mode_that_vanished_falls_back_to_normal(floor):
    floor.cfg.mode = "custom:gone"
    assert floor.mode().id == "normal"
    floor.until = 0.0; floor.tick()                                              # and nothing breaks


def test_the_menu_lists_modes_and_offers_to_save_and_delete(floor):
    floor.save_mode("của tôi"); floor.set_mode("work")
    menu = floor.build_menu()
    sub = next(a.menu() for a in menu.actions() if a.text() == "Chế độ")
    names = [a.text() for a in sub.actions() if a.text()]
    assert names[:6] == ["Bình thường", "Làm việc", "Chơi đùa", "Ngủ", "Yên lặng", "của tôi"]
    assert "Lưu cài đặt hiện tại thành chế độ..." in names and "Xoá chế độ của tôi" in names
    assert [a.isChecked() for a in sub.actions()[:6]] == [False, True, False, False, False, False]
    sub.actions()[2].trigger()
    assert floor.cfg.mode == "play"


def test_the_dialog_switches_mode_and_follows_changes_made_from_elsewhere(floor):
    floor.open_settings(); d = floor.dialog                                     # the window the pet itself opened
    assert isinstance(d, SettingsDialog)
    try:
        assert d.mode.currentData() == "normal"
        d.mode.setCurrentIndex(d.mode.findData("play"))
        assert floor.cfg.mode == "play" and d.speed.value() == 150 and d.activity.value() == 200 and d.boxes["chase"].isChecked()
        floor.set_mode("quiet")                                                  # chosen from the menu while the window is open
        assert d.mode.currentData() == "quiet" and d.boxes["quiet"].isChecked() and d.speed.value() == 100
        assert d.speed.label.text() == "100%"
        floor.cfg.speed = 1.3; floor.save_mode("mới")
        assert d.mode.findData("custom:mới") >= 0 and d.mode.currentData() == "custom:mới"
    finally:
        d.close()


def test_the_dbus_api_can_switch_modes(floor):
    from mochi.api import Api
    a = Api(floor)
    assert a.setMode("Ngủ") is True and floor.cfg.mode == "sleep"
    assert a.setMode("khong co") is False and a.setMode("\x00") is False and a.setMode("") is False and floor.cfg.mode == "sleep"


def test_the_pomodoro_still_wins_over_a_mode_that_would_wander(floor, monkeypatch):
    floor.set_mode("play")
    floor.start_focus(25)
    floor.until = 0.0; floor.tick()
    assert floor.state == State(action=Action.WORK) and mp is not None
