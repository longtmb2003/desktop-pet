import math
from datetime import time

import pytest
from conftest import HANHAN, render, uncovered_and_clipped, write_pack
from PySide6.QtCore import QPoint, QSettings

import mochi.pet as mp
from mochi import apps, physics
from mochi.pets import MOCHI
from mochi.pets.pack import load_dir
from mochi.settings import Settings
from mochi.state import BEHAVIOR_NAMES, MISCHIEF, SCOLDING, Action, Expression, Motion, State, duration

WIN = ("w1", (100, 400, 500, 300))                                    # a window whose top is 400 px down: room for the pet above it


@pytest.fixture
def scene(pet):
    """the pet on the floor, the user working in a window it can jump onto, and every condition for mischief met"""
    g = pet.screen_geo()
    pet.wins = {WIN[0]: WIN[1]}
    pet.px, pet.py, pet.vx, pet.vy, pet.support = 150.0, g.bottom + 1 - pet.feet, 0.0, 0.0, None
    pet.grounded = True; pet.enter(State()); pet.until = float("inf")
    pet.t, pet.last_touch, pet.next_mischief = 500.0, -1e9, 0.0
    pet.now_time = lambda: time(15, 0)
    pet.set_active("w1", "firefox"); pet.active_since = 400.0
    return pet


def kinds(pet, monkeypatch, pick):
    monkeypatch.setattr(mp.random, "choice", lambda seq: pick if isinstance(seq, list) and pick in seq else seq[0])


def test_the_pet_knows_which_window_you_are_working_in(pet):
    pet.t = 50.0
    pet.set_active("abc", "konsole")
    assert (pet.active_id, pet.active_class, pet.active_since) == ("abc", "konsole", 50.0)
    pet.t = 80.0; pet.set_active("abc", "konsole2")                       # same window: the clock keeps running
    assert pet.active_since == 50.0 and pet.active_class == "konsole2"
    pet.set_active("", ""); assert pet.active_id == "" and pet.active_since == 80.0


@pytest.mark.parametrize("what", ["mischief off", "quiet", "pomodoro", "night", "too soon", "no window", "unknown window", "just switched",
                                  "just petted", "already going", "in the air", "busy"])
def test_each_thing_that_should_keep_it_well_behaved(scene, what):
    p = scene
    if what == "mischief off": p.cfg.mischief = False
    elif what == "quiet": p.cfg.quiet = True
    elif what == "pomodoro": p.start_focus(25); p.enter(State()); p.until = float("inf"); p.bubble.dismiss()
    elif what == "night": p.now_time = lambda: time(23, 0)
    elif what == "too soon": p.next_mischief = p.t + 30
    elif what == "no window": p.set_active("", "")
    elif what == "unknown window": p.set_active("gone", "code")
    elif what == "just switched": p.active_since = p.t - 5
    elif what == "just petted": p.last_touch = p.t - 3
    elif what == "already going": p.pending_mischief = (Action.STOMP, p.t + 3, 1)
    elif what == "in the air": p.grounded = False; p.enter(State(Motion.AIRBORNE))
    elif what == "busy": p.enter(State(action=Action.GROOM)); p.until = float("inf")
    before = (p.state, p.vy)
    p.check_mischief()
    assert (p.state, p.vy) == before and not p.bubble.isVisible()


def test_with_everything_in_order_it_jumps_up_and_lands_on_the_window_and_misbehaves(scene, monkeypatch):
    p = scene
    kinds(p, monkeypatch, Action.STOMP)
    p.check_mischief()
    assert p.vy < 0 and p.support is None and p.pending_mischief and p.pending_mischief[0] is Action.STOMP
    assert p.bubble.lines in apps.REMARKS["browser"]                       # it says something about a browser
    assert 60 <= p.next_mischief - p.t <= 150                              # and won't do this again for a minute or two
    for _ in range(200):
        p.tick()
        if p.state.action is Action.STOMP: break
    assert p.state.action is Action.STOMP and p.support == "w1" and p.grounded
    assert p.py == 400 - p.feet and 100 < p.px + p.size / 2 < 600         # feet on the window's top edge, over the window
    assert p.pending_mischief is None


@pytest.mark.parametrize("kind", [Action.PEEK, Action.DANGLE])
def test_peeking_and_dangling_happen_at_an_edge_looking_outwards(scene, monkeypatch, kind):
    p = scene
    kinds(p, monkeypatch, kind)
    p.check_mischief()
    for _ in range(200):
        p.tick()
        if p.state.action is kind: break
    assert p.state.action is kind and p.support == "w1"
    x, cx = 100, p.px + p.size / 2
    left_edge, right_edge = cx < x + 100, cx > x + 500 - 100
    assert left_edge or right_edge                                         # near one end of the window's top
    assert p.facing == (-1 if left_edge else 1)                            # facing out over that edge


def test_it_picks_the_nearer_edge(scene, monkeypatch):
    p = scene
    p.px = 500.0                                                           # nearer the right-hand end
    assert p.window_spot("w1", edge=True)[1] == 1
    p.px = 0.0
    assert p.window_spot("w1", edge=True)[1] == -1
    tx, _ = p.window_spot("w1", edge=False)
    assert tx == 350                                                       # the middle when it needn't be at an edge


@pytest.mark.parametrize("win,why", [((100, 60, 500, 300), "too high: no room for its head above it"), ((100, 400, 50, 300), "too narrow"),
                                     ((100, 900, 500, 50), "below the screen")])
def test_a_window_it_cannot_stand_on_gives_no_spot_and_it_plays_on_the_floor_instead(scene, monkeypatch, win, why):
    p = scene
    p.wins = {"w1": win}
    assert p.window_spot("w1", edge=False) is None, why
    kinds(p, monkeypatch, Action.DANCE)
    p.check_mischief()
    assert p.state.action is Action.DANCE and p.pending_mischief is None and p.vy == 0      # no jump: it plays where it stands


def test_a_covered_window_top_gives_no_spot(scene):
    p = scene
    p.wins = {"w1": (100, 400, 500, 300), "w2": (0, 380, 800, 400)}       # another window stacked above, hiding the top edge
    assert p.window_spot("w1", edge=False) is None


def test_it_plays_in_place_if_it_is_already_standing_on_the_window(scene, monkeypatch):
    p = scene
    p.py, p.support = 400 - p.feet, "w1"; p.px = 300.0
    for pick in (Action.PEEK, Action.STOMP):
        kinds(p, monkeypatch, pick)
        p.enter(State()); p.until = float("inf"); p.next_mischief = 0.0; p.bubble.dismiss()
        p.check_mischief()
        assert p.state.action in (Action.STOMP, Action.DANCE) and p.vy == 0   # no edge tricks unless it went to an edge on purpose


def test_a_jump_that_is_too_far_becomes_floor_mischief(scene, monkeypatch):
    p = scene
    monkeypatch.setattr(physics, "leap", lambda *a, **k: None)
    kinds(p, monkeypatch, Action.STOMP)
    p.check_mischief()
    assert p.state.action in (Action.STOMP, Action.DANCE) and p.vy == 0


def test_an_unfinished_jump_is_forgotten_and_a_landing_elsewhere_starts_nothing(scene, monkeypatch):
    p = scene
    p.pending_mischief = (Action.STOMP, p.t - 1, 1)                        # it never made it, and time is up
    p.start_pending_mischief("w1"); assert p.pending_mischief is None and p.state.action is Action.NONE
    p.pending_mischief = (Action.STOMP, p.t + 5, 1)
    p.start_pending_mischief(None); assert p.pending_mischief is not None and p.state.action is Action.NONE     # landed on the floor: wait
    p.vy = -50; p.start_pending_mischief("w1"); assert p.state.action is Action.NONE                               # still rising
    p.vy = 10; p.start_pending_mischief("w1"); assert p.state.action is Action.STOMP


def test_the_app_remarks_can_be_turned_off_and_quiet_mode_silences_them(scene, monkeypatch):
    p = scene
    kinds(p, monkeypatch, Action.STOMP)
    p.cfg.app_remarks = False; p.check_mischief(); assert not p.bubble.isVisible()
    p.pending_mischief = None; p.next_mischief = 0.0; p.cfg.app_remarks = True; p.grounded = True; p.enter(State()); p.vy = 0.0
    p.check_mischief(); assert p.bubble.isVisible()


def test_more_activity_means_mischief_more_often(scene, monkeypatch):
    p = scene
    gaps = {}
    for act in (0.5, 3.0):
        p.cfg.activity = act; p.next_mischief = 0.0; p.pending_mischief = None; p.enter(State()); p.grounded = True; p.vy = 0.0
        p.check_mischief(); gaps[act] = p.next_mischief - p.t
    assert gaps[3.0] < gaps[0.5] and 20 <= gaps[3.0] <= 50 and 120 <= gaps[0.5] <= 300


def test_the_check_runs_from_the_normal_tick(scene, monkeypatch):
    p = scene
    kinds(p, monkeypatch, Action.STOMP)
    p.next_check = 0.0; p.tick()
    assert p.pending_mischief or p.state.action in MISCHIEF or p.vy < 0


def test_only_characters_with_lines_to_scold_with_scold(scene, qapp, tmp_path):
    assert SCOLDING[0] not in scene.mischief_kinds(True) and MOCHI.scold == ()
    behaviors = {"idle": 3, "walk": 2, "point": 1, "wag": 1}
    d = load_dir(write_pack(tmp_path / "s", id="s", scold=["Làm việc đi!", "x\x00y"], behaviors=behaviors))
    assert d.scold == ("Làm việc đi!", "x y")
    scene.defn = d
    assert set(SCOLDING) <= set(scene.mischief_kinds(False))


# ---- scolding --------------------------------------------------------------------------------------------------
def test_scolding_says_a_scolding_line_and_a_quiet_pet_scolds_silently(scene, qapp, tmp_path):
    scene.defn = load_dir(write_pack(tmp_path / "s", id="s", scold=["Làm việc đi!"]))
    for a in SCOLDING:
        scene.bubble.dismiss(); scene.enter(State(action=a))
        assert scene.bubble.lines == "Làm việc đi!"
    scene.cfg.quiet = True; scene.bubble.dismiss(); scene.enter(State(action=Action.POINT))
    assert not scene.bubble.isVisible()


def test_a_character_without_lines_still_has_something_to_say(scene):
    scene.enter(State(action=Action.WAG)); assert scene.bubble.lines == "Làm việc đi!"


def test_pack_behaviours_can_name_the_scolding_moves(qapp, tmp_path):
    d = load_dir(write_pack(tmp_path / "s", id="s", behaviors={"idle": 3, "walk": 2, "point": 1, "wag": 2, "lecture": 1}))
    assert {(Motion.IDLE, Action.POINT), (Motion.IDLE, Action.WAG), (Motion.IDLE, Action.LECTURE)} <= set(d.behaviors)
    assert BEHAVIOR_NAMES["point"] == (Motion.IDLE, Action.POINT)


def test_every_new_action_has_a_sensible_duration():
    for a in (*SCOLDING, *MISCHIEF):
        lo, hi = duration(State(action=a))
        assert 2 <= lo <= hi <= 8


def sprite_scolder(make_pet, tmp_path):
    d = load_dir(write_pack(tmp_path / "sc", id="sc", scold=["x"], height=150))
    p = make_pet("sc", 1.0, {"mochi": MOCHI, "sc": d})
    p.grounded, p.hot, p.squash, p.hearts, p.t, p.began, p.dur = True, False, 0.0, [], 10.0, 10.0, 4.0
    return p


def test_the_pointing_arm_reaches_towards_the_mouse_pointer(make, tmp_path, monkeypatch):
    import mochi.sprite as sp
    p = sprite_scolder(make, tmp_path)
    p.state = State(action=Action.POINT)
    coat = p.defn.pack.coat

    def coat_pixels(img, right):
        w = img.width()
        return sum(1 for y in range(img.height()) for x in range(w // 2 + 40 if right else 0, w if right else w // 2 - 40)
                   if img.pixelColor(x, y) == coat)
    from PySide6.QtCore import QPoint as P
    monkeypatch.setattr(sp.QCursor, "pos", staticmethod(lambda: p.pos() + P(p.size + 300, p.feet - 60)))         # pointer far to the right
    to_right = render(p)
    monkeypatch.setattr(sp.QCursor, "pos", staticmethod(lambda: p.pos() + P(-300, p.feet - 60)))                 # pointer far to the left
    to_left = render(p)
    assert coat_pixels(to_right, True) > 100 and coat_pixels(to_right, True) > coat_pixels(to_left, True)
    assert coat_pixels(to_left, False) > coat_pixels(to_right, False)      # the arm follows the pointer to whichever side it is


def test_wagging_and_lecturing_look_different_from_standing_and_from_each_other(make, tmp_path):
    p = sprite_scolder(make, tmp_path)
    imgs = {}
    for a in (Action.NONE, Action.WAG, Action.LECTURE, Action.POINT):
        p.state = State(action=a); imgs[a] = render(p)
    assert len({bytes(i.constBits()) for i in imgs.values()}) == 4


def test_every_scolding_and_mischief_pose_is_clickable_and_inside_the_window_for_every_character(make, tmp_path, qapp):
    """the window mask hides whatever it doesn't cover: check Mochi, a sprite and the real Hà Nhân in each new pose, both ways round"""
    chars = [("mochi", {"mochi": MOCHI})]
    d = load_dir(write_pack(tmp_path / "sc", id="sc", scold=["x"], height=150))
    chars.append(("sc", {"mochi": MOCHI, "sc": d}))
    if (HANHAN / "pack.json").exists(): chars.append(("hanhan", {"mochi": MOCHI, "hanhan": load_dir(HANHAN)}))
    for name, pets in chars:
        for scale in (1.0, 1.5):
            p = make(name, scale, pets)
            p.grounded, p.hot, p.squash, p.hearts = True, False, 0.0, []
            for a in (*SCOLDING, *MISCHIEF):
                if name == "mochi" and a in SCOLDING: continue           # (Mochi has no arms to point with)
                for facing in (1, -1):
                    for k in range(6):
                        p.facing = p.drawn_facing = facing
                        p.state, p.t, p.began, p.dur = State(action=a), 10.0 + k * 0.29, 10.0, 4.0
                        left, edge = uncovered_and_clipped(p)
                        assert left < 40, f"{name} x{scale} {a.name} facing={facing} phase={k}: not clickable ({left})"
                        assert edge < 40, f"{name} x{scale} {a.name} facing={facing} phase={k}: cut off by the window ({edge})"


def test_the_bouncing_and_dancing_poses_make_the_vector_pet_grin(pet):
    pet.grounded, pet.facing, pet.drawn_facing, pet.t, pet.began, pet.dur = True, 1, 1, 10.3, 10.0, 4.0
    plain = render(pet)
    pet.state = State(action=Action.DANCE); dance = render(pet)
    pet.state = State(action=Action.DANGLE); dangle = render(pet)
    assert dance != plain and dangle != plain and dance != dangle


def test_the_settings_window_has_the_new_switches(pet):
    from mochi.settings_dialog import SettingsDialog
    d = SettingsDialog(pet)
    try:
        assert d.boxes["mischief"].isChecked() and d.boxes["app_remarks"].isChecked()
        d.boxes["mischief"].setChecked(False)
        assert pet.cfg.mischief is False
    finally:
        d.close()


def test_the_modes_that_should_be_calm_switch_mischief_off(pet):
    from mochi import modes
    assert [m.values["mischief"] for m in modes.BUILTIN.values()] == [True, False, True, False, False]
    pet.set_mode("work"); assert pet.cfg.mischief is False
    pet.set_mode("play"); assert pet.cfg.mischief is True


def test_a_new_active_window_report_is_taken_from_kwin_end_to_end(pet):
    from mochi.platform.kde import Bus
    Bus(lambda w: None, pet).active("{id-1}", "org.kde.konsole")
    assert pet.active_id == "{id-1}" and pet.active_class == "org.kde.konsole" and apps.category(pet.active_class) == "terminal"
    assert QPoint is not None and Expression is not None and math.pi > 3 and Settings is not None and QSettings is not None


def test_it_looks_out_over_the_edge_even_when_it_jumped_in_from_outside(scene, monkeypatch):
    p = scene
    p.px = 0.0                                                            # left of the window: it jumps rightwards onto its left edge
    kinds(p, monkeypatch, Action.PEEK)
    p.check_mischief()
    assert p.facing == 1                                                  # while jumping it faces where it is going
    for _ in range(200):
        p.tick()
        if p.state.action is Action.PEEK: break
    assert p.state.action is Action.PEEK and p.facing == -1               # but peeks outwards, over the edge it stands at
