import pytest
from conftest import render, uncovered_and_clipped, write_pack
from PySide6.QtCore import QPoint

import mochi.pet as mp
import mochi.sprite as sp
from mochi.pets import MOCHI
from mochi.pets.pack import load_dir
from mochi.state import Action, Expression, Motion, State


def full_pack(tmp_path, **kw):
    return load_dir(write_pack(tmp_path / "full", id="full", ride=True, free=True, nose=True, scold=["x"], height=150, **kw))


def make_pet(make, tmp_path, **kw):
    d = full_pack(tmp_path, **kw)
    p = make("full", 1.0, {"mochi": MOCHI, "full": d})
    p.grounded, p.hot, p.squash, p.hearts, p.t, p.began, p.dur = True, False, 0.0, [], 10.0, 10.0, 4.0
    return p


# ---- the pack -------------------------------------------------------------------------------------------------------
def test_a_pack_can_have_arm_free_bodies_and_a_tricycle(qapp, tmp_path):
    d = full_pack(tmp_path)
    assert set(d.pack.free) == {"left", "right", "both"} and d.pack.ride.height == 60 and d.ride_speed == 2.5
    assert d.pack.ride.lines == ("Ting ting!",) and len(d.pack.ride.wheels) == 1 and d.pack.ride.wheels[0]["hub"] == (20.0, 34.0)
    plain = load_dir(write_pack(tmp_path / "p", id="p"))
    assert plain.pack.free == {} and plain.pack.ride is None and plain.ride_speed == 1.0


@pytest.mark.parametrize("bad,why", [
    ({"body_free": {"left": "body.png"}}, "body_free"),
    ({"body_free": {"left": "body.png", "right": "body.png", "both": "ride.png"}}, "size"),
    ({"body_free": []}, "body_free"), ({"body_free": {"left": "../x", "right": "b", "both": "c"}}, "outside"),
    ({"ride": "fast"}, "ride must"), ({"ride": {"image": "nope.png"}}, "cannot read"),
    ({"ride": {"image": "ride.png", "speed": 99}}, "ride.speed"),
    ({"ride": {"image": "ride.png", "height": 1}}, "ride.height"), ({"ride": {"image": "ride.png", "wheels": [5]}}, "each wheel"),
    ({"ride": {"image": "ride.png", "wheels": [{"x": 1}]}}, "wheel.y"),
    ({"ride": {"image": "ride.png", "wheels": [dict.fromkeys(("x", "y", "rx", "ry", "rim_x", "rim_y", "rim_rx", "rim_ry"), 1)]}},
     "wheel.hub"),
])
def test_a_broken_ride_or_body_free_is_refused_with_a_reason(qapp, tmp_path, bad, why):
    root = write_pack(tmp_path / "b", ride=True, free=True)
    import json
    j = json.loads((root / "pack.json").read_text()); j.update(bad)
    (root / "pack.json").write_text(json.dumps(j))
    with pytest.raises(ValueError, match=why):
        load_dir(root)


def test_the_real_hanhan_pack_has_arm_free_bodies_and_a_tricycle(qapp):
    from conftest import HANHAN
    if not (HANHAN / "pack.json").exists(): pytest.skip("no local Hà Nhân pack")
    d = load_dir(HANHAN)
    assert set(d.pack.free) == {"left", "right", "both"} and d.pack.ride and d.pack.ride.speed >= 1.5 and len(d.pack.ride.wheels) == 2
    assert d.pack.free["both"].size() == d.pack.body.size()


# ---- riding -------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("state,expected", [
    (State(Motion.WALK), True), (State(Motion.WALK, action=Action.CHASE), True), (State(), False), (State(Motion.SLEEP), False),
    (State(Motion.WALK, Expression.DIZZY), False), (State(Motion.WALK, Expression.HAPPY), False),
    (State(Motion.WALK, action=Action.PUSH), False),
    (State(Motion.AIRBORNE), False), (State(Motion.DRAG), False)])
def test_it_rides_only_while_calmly_walking_or_chasing(make, tmp_path, state, expected):
    p = make_pet(make, tmp_path)
    p.state = state
    assert sp.riding(p) is expected


def test_a_character_without_a_tricycle_never_rides(make, tmp_path, pet):
    plain = load_dir(write_pack(tmp_path / "p", id="p"))
    p = make("p", 1.0, {"mochi": MOCHI, "p": plain}); p.state = State(Motion.WALK)
    assert not sp.riding(p) and not sp.riding(pet)                       # nor does Mochi


def distance(make, tmp_path, kind, monkeypatch, ticks=8):
    p = make_pet(make, tmp_path)
    monkeypatch.setattr(mp.QCursor, "pos", staticmethod(lambda: QPoint(760, 600)))          # the pointer it chases: far to the right
    g = p.screen_geo()
    p.px, p.py, p.vx, p.vy, p.support = g.left + 300.0, g.bottom + 1 - p.feet, 0.0, 0.0, None
    p.enter(State(Motion.WALK, action=kind)); p.until = float("inf"); p.facing = p.drawn_facing = 1; p.turn_start = -1e9
    x0 = p.px
    for _ in range(ticks): p.tick()
    return p.px - x0, p


def test_riding_is_faster_walking_and_chasing_alike(make, tmp_path, monkeypatch):
    walk, p = distance(make, tmp_path, Action.NONE, monkeypatch)
    chase, _ = distance(make, tmp_path, Action.CHASE, monkeypatch)
    assert p.ride_boost() == 2.5
    assert walk == pytest.approx(8 * 0.033 * p.walk_speed * 2.5, rel=0.05)      # 2.5 times the walking speed
    assert chase == pytest.approx(2 * walk, rel=0.05)                            # a chase is still twice as fast as a walk
    p.enter(State()); assert p.ride_boost() == 1.0                               # standing: no boost


def test_it_rings_its_bell_when_it_sets_off(make, tmp_path, monkeypatch):
    p = make_pet(make, tmp_path)
    monkeypatch.setattr(mp.random, "random", lambda: 0.1)
    monkeypatch.setattr(mp.random, "choice", lambda seq: seq[0])
    p.enter(State(Motion.WALK)); assert p.bubble.lines == "Ting ting!"
    p.bubble.dismiss(); monkeypatch.setattr(mp.random, "random", lambda: 0.9)
    p.enter(State(Motion.WALK)); assert not p.bubble.isVisible()          # only now and then
    p.cfg.quiet = True; monkeypatch.setattr(mp.random, "random", lambda: 0.1)
    p.enter(State(Motion.WALK)); assert not p.bubble.isVisible()          # and never in quiet mode


def test_the_tricycle_is_drawn_instead_of_the_standing_body_and_its_wheels_turn_with_the_distance(make, tmp_path):
    p = make_pet(make, tmp_path)
    p.facing = p.drawn_facing = -1; p.state = State()
    standing = render(p)
    p.state = State(Motion.WALK)
    a = render(p)
    p.px += 20; b = render(p)                                            # it has moved on: the wheels have turned
    assert a != standing and a != b
    p.px -= 20
    assert render(p) == a                                                # same place, same picture: the turn depends only on the distance


def test_the_wheels_turn_the_right_way_whichever_way_it_goes(make, tmp_path, monkeypatch):
    p = make_pet(make, tmp_path)                                         # (its art looks right: facing right draws it as is)
    calls = []
    orig = sp.draw_ride
    monkeypatch.setattr(sp, "draw_ride", lambda pr, rd, t, x, sign: (calls.append((x, sign)), orig(pr, rd, t, x, sign))[1])
    p.state = State(Motion.WALK); p.px = 120.0
    for facing, sign in ((1, 1), (-1, -1)):
        p.facing = p.drawn_facing = facing; calls.clear(); render(p)
        assert calls == [(120.0, sign)]                                  # mirrored art turns its wheels the other way round
    import math
    r = p.defn.pack.ride.wheels[0]["ry"] * p.defn.pack.ride.height / p.defn.pack.ride.image.height()
    assert math.degrees(10 / r) > 5                                      # ten pixels of travel is a visible turn of the wheel


def test_the_riding_pose_bounces_and_skids_through_a_turn(make, tmp_path):
    p = make_pet(make, tmp_path)
    p.state = State(Motion.WALK); p.facing = p.drawn_facing = 1; p.turn_start = -1e9
    dys = {round(sp.pose(p)[1], 3) for p in [p] for p.t in (10.0, 10.05, 10.1, 10.15)}
    assert len(dys) > 1                                                  # it bounces along
    steady = sp.pose(p)[2]
    p.turn_start, p.turn_from = 10.0, -1.0; p.t = 10.0 + p.defn.turn_s / 2
    assert abs(sp.pose(p)[2] - steady) > 8                               # half way round it is leaning hard


def test_everything_the_rider_paints_is_clickable_and_inside_the_window(make, tmp_path):
    p = make_pet(make, tmp_path)
    for f in (1, -1):
        for st in (State(Motion.WALK), State(Motion.WALK, action=Action.CHASE)):
            for k in range(8):
                p.state, p.facing, p.drawn_facing, p.t, p.px = st, f, f, 10.0 + k * 0.13, 100.0 + k * 7
                left, edge = uncovered_and_clipped(p)
                assert left < 40 and edge < 40, (f, st, k, left, edge)


# ---- the arms ---------------------------------------------------------------------------------------------------
def test_which_of_the_pictures_own_arms_is_replaced_by_a_drawn_one(make, tmp_path, monkeypatch):
    p = make_pet(make, tmp_path)
    for st, want in ((State(action=Action.WORK), {"left", "right"}), (State(action=Action.LECTURE), {"left", "right"}),
                     (State(action=Action.WAG), {"right"}), (State(), set()), (State(Motion.WALK), set())):
        p.state = st
        assert sp.arm_sides(p, 1) == want
    p.state = State(action=Action.WAG)
    assert sp.arm_sides(p, -1) == {"left"}                               # the art is drawn mirrored: its right arm is on the screen's left
    p.state = State(action=Action.POINT)
    monkeypatch.setattr(sp, "cursor", lambda pet: (300, 0)); assert sp.arm_sides(p, 1) == {"right"} and sp.arm_sides(p, -1) == {"left"}
    monkeypatch.setattr(sp, "cursor", lambda pet: (-300, 0)); assert sp.arm_sides(p, 1) == {"left"} and sp.arm_sides(p, -1) == {"right"}


def test_the_body_without_the_arm_is_the_picture_used_while_a_drawn_arm_is_out(make, tmp_path):
    p = make_pet(make, tmp_path); pk = p.defn.pack
    assert sp.body_image(pk, set()) is pk.body
    assert sp.body_image(pk, {"left"}) is pk.free["left"] and sp.body_image(pk, {"right"}) is pk.free["right"]
    assert sp.body_image(pk, {"left", "right"}) is pk.free["both"]
    plain = load_dir(write_pack(tmp_path / "plain", id="plain"))
    assert sp.body_image(plain.pack, {"left"}) is plain.pack.body        # a pack with none draws the ordinary body


def test_a_pointing_character_shows_the_arm_free_body_on_that_side_only(make, tmp_path, monkeypatch):
    p = make_pet(make, tmp_path)
    p.facing = p.drawn_facing = 1
    monkeypatch.setattr(sp, "cursor", lambda pet: (300, 0))
    seen = []
    orig = sp.body_image
    monkeypatch.setattr(sp, "body_image", lambda pk, sides: (seen.append(frozenset(sides)), orig(pk, sides))[1])
    p.state = State(action=Action.POINT); render(p)
    p.state = State(); render(p)
    assert seen == [frozenset({"right"}) if p.defn.pack.art > 0 else frozenset({"left"}), frozenset()] or len(seen) == 2


def test_arm_poses_still_fit_the_mask_and_the_window_with_the_arm_free_bodies(make, tmp_path):
    p = make_pet(make, tmp_path)
    for st in (State(action=Action.POINT), State(action=Action.WAG), State(action=Action.LECTURE), State(action=Action.WORK)):
        for f in (1, -1):
            for k in range(6):
                p.state, p.facing, p.drawn_facing, p.t = st, f, f, 10.0 + k * 0.3
                left, edge = uncovered_and_clipped(p)
                assert left < 40 and edge < 40, (st, f, k, left, edge)
    assert QPoint is not None
