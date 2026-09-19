
import pytest
from conftest import HANHAN, render, uncovered_and_clipped, write_pack
from PySide6.QtCore import QPoint

from mochi.pets import MOCHI
from mochi.pets.pack import load_dir
from mochi.physics import FEET, S
from mochi.state import Action, Expression, Motion, State


def floor_y(p):
    return p.screen_geo().bottom + 1 - p.feet


def test_the_window_takes_the_pets_size_and_scale(make):
    p = make("blob", 1.5)
    assert (p.width(), p.height(), p.size, p.feet, p.top) == (300, 300, 300, 285, 60)
    assert p.walk_speed == pytest.approx(45.0)
    m = make("mochi")
    assert (m.width(), m.feet, m.top) == (S, FEET, 40) and m.head == pytest.approx(190)            # Mochi unchanged at scale 1


@pytest.mark.parametrize("name,scale", [("mochi", 1.0), ("mochi", 1.7), ("blob", 1.0), ("blob", 0.6), ("blob", 2.0)])
def test_it_falls_and_lands_with_its_feet_on_the_floor(make, name, scale):
    p = make(name, scale)
    g = p.screen_geo()
    p.px, p.py, p.vy, p.vx = g.left + 300, g.top - 100, 0.0, 0.0
    p.enter(State(Motion.AIRBORNE))
    for _ in range(900):
        p.tick()
        if p.state.motion is not Motion.AIRBORNE: break
    assert p.grounded and p.py == floor_y(p) and p.state.motion is Motion.IDLE


def test_it_stands_on_a_window_top_at_its_own_foot_line(make):
    p = make("blob", 1.0)
    g = p.screen_geo()
    top = g.top + 400
    p.wins = {"w": (g.left + 100, top, 600, 300)}
    p.px, p.py, p.vy, p.vx, p.support = g.left + 300, top - p.feet, 0.0, 0.0, "w"
    p.enter(State()); p.tick()
    assert p.support == "w" and p.grounded and p.py == top - p.feet


def test_a_taller_pet_needs_more_headroom_to_stand_on_a_window_near_the_screen_top(make):
    g = make("mochi").screen_geo()
    m, b = make("mochi"), make("blob")
    for p in (m, b):
        p.wins = {"w": (g.left + 100, g.top + 210, 600, 200)}          # only 210 px below the screen top
        p.px, p.py, p.vy, p.vx, p.support = g.left + 300, g.top + 210 - p.feet, 0.0, 0.0, None
        p.enter(State()); p.tick()
    assert m.support == "w"                                              # Mochi (head 190) fits
    assert b.support is None                                             # the blob (height 150 + 84 = 234) does not


def test_switching_character_keeps_the_feet_and_drops_stale_speech(make):
    p = make("mochi")
    p.px, p.py = 700.0, 500.0
    feet_x, feet_y = p.px + p.size / 2, p.py + p.feet
    p.say("hello", urgent=True); assert p.bubble.isVisible()
    p.cfg.pet = "blob"; p.apply_settings()
    assert p.defn.id == "blob" and (p.width(), p.height()) == (200, 200)
    assert (p.px + p.size / 2, p.py + p.feet) == (feet_x, feet_y) and not p.bubble.isVisible()
    p.cfg.scale = 2.0; p.apply_settings()
    assert p.width() == 400 and p.px + p.size / 2 == feet_x and p.py + p.feet == feet_y
    p.cfg.pet = "no-such-pet"; p.apply_settings()
    assert p.defn.id == "blob"                                           # an unknown id changes nothing


def test_the_menu_lists_characters_only_when_there_is_a_choice(make):
    p = make("blob")
    who = [a for a in p.build_menu().actions() if a.text() == "Nhân vật"]
    assert who and [a.text() for a in who[0].menu().actions()] == ["Mochi", "Blob"]
    assert [a.isChecked() for a in who[0].menu().actions()] == [False, True]
    who[0].menu().actions()[0].trigger()                                 # choose Mochi from the menu
    assert p.defn.id == "mochi" and p.cfg.pet == "mochi"
    p.pets = {"mochi": MOCHI}
    assert "Nhân vật" not in [a.text() for a in p.build_menu().actions()]


def test_its_own_words_and_scream_come_from_the_definition(make, monkeypatch):
    p = make("blob")
    p.grounded = True; p.enter(State()); p.next_chat = 0.0
    monkeypatch.setattr("mochi.pet.random.choice", lambda seq: seq[-1])
    p.tick()
    assert p.bubble.lines == "Hello"
    p.bubble.dismiss()
    p.wins = {"w": (0, 700, 800, 200)}; p.support = "w"; p.py = 700 - p.feet; p.vy = 0
    p.wins = {}; p.tick()
    assert p.bubble.lines == "Waaah!"


def test_the_definitions_behaviours_decide_what_it_does_next(make):
    import mochi.state as st
    p = make("blob")
    seen = set()
    for _ in range(300):
        p.enter(State()); p.until = 0.0; p.grounded = True; p.py = floor_y(p); p.tick()
        seen.add((p.state.motion, p.state.action))
    assert Action.CHASE not in {a for _, a in seen} and Action.GROOM not in {a for _, a in seen}         # not in its list
    assert (Motion.IDLE, Action.RANT) in seen or (Motion.WALK, Action.NONE) in seen
    assert set(st.BEHAVIORS) != set(p.defn.behaviors)


def test_ranting_says_something_and_moves_its_mouth(make):
    p = make("blob")
    p.grounded = True
    p.enter(State(action=Action.RANT))
    assert p.bubble.isVisible() and p.bubble.lines in ("Bloop", "Hello")
    from mochi.sprite import face_kind
    assert face_kind(p) == "talk"
    p.cfg.quiet = True; p.bubble.dismiss(); p.enter(State(action=Action.RANT))
    assert not p.bubble.isVisible()                                      # a quiet pet rants silently


def test_the_face_follows_the_mood(make):
    from mochi.sprite import face_kind
    p = make("blob")
    assert face_kind(p) == "neutral"
    p.state = State(expression=Expression.HAPPY); assert face_kind(p) == "laugh"
    p.state = State(Motion.AIRBORNE, Expression.SCARED); assert face_kind(p) == "talk"
    p.state = State(Motion.SLEEP); p.say("x", urgent=True); assert face_kind(p) == "neutral"        # asleep: no mouthing


STATES = [State(), State(Motion.WALK), State(Motion.WALK, Expression.DIZZY), State(expression=Expression.HAPPY), State(Motion.SLEEP),
          State(Motion.AIRBORNE, Expression.SCARED), State(Motion.DRAG), State(action=Action.FLIP), State(action=Action.WORK),
          State(Motion.WALK, action=Action.PUSH), State(Motion.WALK, action=Action.CHASE), State(action=Action.RANT),
          State(action=Action.YAWN)]


@pytest.mark.parametrize("scale", [0.6, 1.0, 1.7])
def test_everything_painted_is_clickable_and_inside_the_window(make, scale):
    """the window mask hides whatever it doesn't cover, so it must cover every visible pixel in every pose, facing and phase"""
    p = make("blob", scale)
    for facing in (1, -1):
        for state in STATES:
            for hot in (False, True):
                for k in range(5):
                    p.facing, p.state, p.hot, p.squash = facing, state, hot, 0.0
                    p.grounded = state.motion not in (Motion.DRAG, Motion.AIRBORNE)
                    p.t, p.began, p.dur, p.hearts = 10.0 + k * 0.6, 10.0, 3.0, ([[5, -60, 1.0]] if k == 3 else [])
                    left, edge = uncovered_and_clipped(p)
                    assert left < 40, f"visible but not clickable (alpha {left}): {state} facing={facing} hot={hot} phase={k}"
                    assert edge < 40, f"clipped by the window edge (alpha {edge}): {state} facing={facing} phase={k}"


def test_the_sweep_really_detects_a_mask_that_is_too_small(make, monkeypatch):
    import mochi.pet as mp
    from PySide6.QtGui import QRegion
    p = make("blob")
    p.state, p.grounded, p.hearts, p.squash, p.t = State(), True, [], 0.0, 10.0
    orig = mp.sprite_mask
    monkeypatch.setattr(mp, "sprite_mask", lambda pet: orig(pet).intersected(QRegion(0, 0, 40, 40)))
    assert uncovered_and_clipped(p)[0] >= 40


def test_the_mask_is_not_rebuilt_every_frame_and_the_outline_is_cached(make):
    p = make("blob")
    p.grounded = True; p.enter(State()); p.until = float("inf")
    p.py = floor_y(p); p.squash = 0.0
    p.update_mask(); key = p.mask_key
    for _ in range(50): p.tick()
    assert p.mask_key == key and key[2] == "alpha"
    assert len(p.defn.pack.masks) == 1
    p.facing = -1; p.update_mask(); p.facing = 1; p.update_mask()
    assert len(p.defn.pack.masks) == 2                                   # one outline per facing, reused afterwards


def test_a_standing_pet_is_click_through_around_its_outline(make):
    p = make("blob")
    p.grounded = True; p.enter(State()); p.facing = 1; p.squash = 0.0; p.hot = False
    p.mask_key = None; p.update_mask(); m = p.mask()
    assert m.contains(QPoint(p.size // 2, p.feet - 75))                  # on the body
    assert not m.contains(QPoint(2, 2)) and not m.contains(QPoint(p.size - 3, p.feet - 100))       # in the transparent corners


def test_bubble_stays_above_the_sprite_head_and_on_screen(make):
    p = make("blob", 1.5)
    p.say("xin chào", urgent=True)
    g = p.screen_geo()
    for px in (g.left - 80, g.left + 500, g.right - 60):
        p.px, p.py = px, g.top + 300
        p.tick()
        b = p.bubble
        assert g.left <= b.x() and b.x() + b.width() <= g.right + 1
        assert b.y() + b.height() <= p.py + p.top + 4 + 1                                     # its tail points at the top of the head


def test_a_wide_pet_bounces_off_the_side_of_the_screen_at_its_own_width(make):
    from mochi.physics import WALL_PAD
    p = make("blob", 2.0)                                                # window 400 px wide
    g = p.screen_geo()
    p.px, p.py, p.vx, p.vy, p.grounded = g.right - 500.0, g.top + 200.0, 900.0, 0.0, False
    p.enter(State(Motion.AIRBORNE))
    right_limit = g.right - p.size + WALL_PAD
    farthest = p.px
    for _ in range(60):
        p.tick()
        farthest = max(farthest, p.px)
        assert p.px <= right_limit + 1e-6, "went through the right edge (using Mochi's window width?)"
    assert farthest >= right_limit - 1                                   # it did reach the wall, and was stopped exactly there


def test_it_moves_its_mouth_while_its_words_are_up_and_not_otherwise(make):
    from mochi.sprite import face_kind
    p = make("blob")
    p.state = State()
    assert face_kind(p) == "neutral"
    p.say("hi", urgent=True); assert face_kind(p) == "talk"
    p.bubble.dismiss(); assert face_kind(p) == "neutral"


def test_switching_character_silences_the_old_ones_bubble(make):
    p = make("mochi")
    p.say("still talking", urgent=True)
    p.change_pet(p.pets["blob"], 1.0)
    assert not p.bubble.isVisible() and not p.bubble.queue.items


@pytest.mark.parametrize("sway", [4, 20])
def test_a_wide_boxy_pet_with_a_big_waddle_is_never_clipped_by_its_own_mask(qapp, tmp_path, make, sway):
    """a rectangle 150 px wide and 100 tall, waddling up to 20 degrees: turning and leaning sweep its corners far out"""
    wide = load_dir(write_pack(tmp_path / "wide", wide=True, id="wide", height=100, sway=sway))
    p = make("wide", 1.0, {"mochi": MOCHI, "wide": wide})
    for facing in (1, -1):
        for state in STATES:
            for k in range(8):
                p.facing, p.state, p.hot, p.squash = facing, state, False, 0.0
                p.grounded = state.motion not in (Motion.DRAG, Motion.AIRBORNE)
                p.t, p.began, p.dur, p.hearts = 10.0 + k * 0.4, 10.0, 3.0, []
                if state.action is Action.FLIP: p.t, p.began, p.dur = 10.0, 10.0 - 0.55 * k / 8, 0.55       # sweep the whole turn
                left, edge = uncovered_and_clipped(p)
                assert left < 40, f"clipped by the click mask (alpha {left}): {state} facing={facing} phase={k} sway={sway}"


def test_tired_by_request_looks_tired_like_a_hot_cpu_does(make):
    from mochi.sprite import pose
    p = make("blob")
    p.state, p.hot, p.facing, p.t = State(), False, 1, 10.0
    calm = pose(p)
    p.state = State(expression=Expression.TIRED)                         # e.g. setExpression("tired") over DBus
    assert pose(p) != calm


def test_hearts_rise_from_above_the_head_of_whatever_it_is(make):
    p = make("blob", 1.0)
    p.grounded = True; p.enter(State()); p.press = None
    p.pet_it()
    assert all(y == 11 - p.defn.height for _, y, _ in p.hearts)          # not from mid-body: a tall pet's head is far above Mochi's
    m = make("mochi")
    m.grounded = True; m.enter(State()); m.pet_it()
    assert all(y == -95 for _, y, _ in m.hearts)                         # Mochi's hearts are exactly where they always were


@pytest.mark.skipif(not (HANHAN / "pack.json").exists(), reason="the Hà Nhân pack is local-only (artwork not in the repository)")
@pytest.mark.parametrize("scale", [0.6, 1.0, 1.7])
def test_the_real_hanhan_pack_is_never_clipped_in_any_pose(qapp, tmp_path, make, scale):
    real = load_dir(HANHAN)
    p = make("hanhan", scale, {"mochi": MOCHI, "hanhan": real})
    for facing in (1, -1):
        for state in STATES:
            for hot in (False, True):
                for k in range(6):
                    p.facing, p.state, p.hot, p.squash = facing, state, hot, 0.0
                    p.grounded = state.motion not in (Motion.DRAG, Motion.AIRBORNE)
                    p.t, p.began, p.dur, p.hearts = 10.0 + k * 0.53, 10.0, 3.0, []
                    if state.action is Action.FLIP: p.t, p.began, p.dur = 10.0, 10.0 - 0.55 * k / 5, 0.55
                    left, edge = uncovered_and_clipped(p)
                    assert left < 40, f"not clickable (alpha {left}): {state} facing={facing} hot={hot} phase={k}"
                    assert edge < 40, f"cut off by the window edge (alpha {edge}): {state} facing={facing} hot={hot} phase={k}"


@pytest.mark.parametrize("prop", ["laptop", "sign"])
@pytest.mark.parametrize("wide", [False, True])
def test_holding_a_prop_stays_inside_the_mask_and_the_window_and_looks_different(qapp, tmp_path, make, prop, wide):
    d = load_dir(write_pack(tmp_path / f"{prop}{wide}", id="prop", wide=wide, work_prop=prop, height=100 if wide else 150))
    p = make("prop", 1.0, {"mochi": MOCHI, "prop": d})
    from mochi.state import State as S_
    p.grounded, p.hot, p.squash, p.hearts = True, False, 0.0, []
    for facing in (1, -1):
        for k in range(8):
            p.facing, p.state, p.t, p.began, p.dur = facing, S_(action=Action.WORK), 10.0 + k * 0.37, 10.0, 8.0
            left, edge = uncovered_and_clipped(p)
            assert left < 40, (prop, wide, facing, k, left)
            assert wide or edge < 40, (prop, facing, k, edge)                          # (a body as wide as the window touches it anyway)
    p.state = S_(); idle = p.grab().toImage()
    p.state = S_(action=Action.WORK); working = p.grab().toImage()
    assert idle != working                                                   # the prop is really drawn


def test_the_busy_sign_is_red_and_its_text_reads_the_same_whichever_way_it_faces(qapp, tmp_path, make):
    sign = load_dir(write_pack(tmp_path / "s", id="s", work_prop="sign"))
    laptop = load_dir(write_pack(tmp_path / "l", id="l", work_prop="laptop"))
    p = make("s", 1.0, {"mochi": MOCHI, "s": sign, "l": laptop})
    p.grounded, p.hot, p.squash, p.hearts, p.state = True, False, 0.0, [], State(action=Action.WORK)
    p.t, p.began, p.dur = 10.472, 10.0, 8.0                                # 3t = 10 pi: the sign is exactly upright

    def reds(img):
        return sum(1 for y in range(img.height()) for x in range(img.width())
                   if (c := img.pixelColor(x, y)).alpha() > 200 and c.red() > 170 and c.green() < 70 and c.blue() < 80)
    p.facing = 1; right = render(p)
    p.facing = -1; left = render(p)
    assert reds(right) > 300 and reds(left) > 300                          # a big red no-entry sign
    p.defn = laptop; p.mask_key = None; p.facing = 1
    assert reds(render(p)) < 30                                            # the laptop is grey: no red to speak of
    # the plaque under the disc: same pixels facing either way, or the "BẬN" would come out mirrored
    bw = 40 * 150 / 80                                                     # the synthetic body's drawn width
    cy, r = -sign.height * 0.44, bw * 0.30
    x0, y0, w, h = int(sign.size / 2 - bw * 0.2), int(sign.feet + cy + r + 6), int(bw * 0.4), 8
    assert right.copy(x0, y0, w, h) == left.copy(x0, y0, w, h)


# ---- which way the art looks, and turning round -------------------------------------------------------------------
def looks_pets(tmp_path, make):
    right = load_dir(write_pack(tmp_path / "r", id="r", nose=True, looks="right"))
    left = load_dir(write_pack(tmp_path / "l", id="l", nose=True, looks="left"))            # same picture, but it says the art looks left
    pets = {"mochi": MOCHI, "r": right, "l": left}
    a, b = make("r", 1.0, pets), make("l", 1.0, pets)
    for p in (a, b):
        p.grounded, p.hot, p.squash, p.hearts, p.state, p.t = True, False, 0.0, [], State(), 10.0
    return a, b


def different_pixels(x, y):
    return sum(1 for j in range(x.height()) for i in range(x.width()) if x.pixel(i, j) != y.pixel(i, j))


def test_the_art_is_mirrored_so_that_it_always_looks_where_it_walks(qapp, tmp_path, make):
    r, l = looks_pets(tmp_path, make)
    r.facing = 1; l.facing = -1
    assert different_pixels(render(r), render(l)) == 0                     # each walking the way its art looks: drawn as is
    r.facing = -1; l.facing = 1
    assert different_pixels(render(r), render(l)) == 0                     # ... and walking the other way: both mirrored
    r.facing = 1
    assert different_pixels(render(r), render(l)) > 500                    # (same direction, opposite art: really different)

    def nose_x(img):                                                       # where the red nose is, horizontally
        xs = [x for y in range(img.height()) for x in range(img.width())
              if (c := img.pixelColor(x, y)).alpha() > 200 and c.red() > 170 and c.green() < 90]
        return sum(xs) / len(xs)
    r.facing = 1; right_nose = nose_x(render(r))
    r.facing = -1; left_nose = nose_x(render(r))
    assert right_nose > r.size / 2 + 10 and left_nose < r.size / 2 - 10    # the nose leads: right when walking right, left going left
    assert abs((right_nose - r.size / 2) + (left_nose - r.size / 2)) < 2   # and the two are mirror images


def test_the_click_mask_follows_the_mirroring(qapp, tmp_path, make):
    r, l = looks_pets(tmp_path, make)
    for p, f in ((r, 1), (l, -1), (r, -1), (l, 1)):
        p.facing = f
        left, edge = uncovered_and_clipped(p)
        assert left < 40 and edge < 40


def test_a_pack_says_which_way_it_looks_and_bad_values_are_refused(qapp, tmp_path):
    assert load_dir(write_pack(tmp_path / "a", id="a")).pack.art == 1
    assert load_dir(write_pack(tmp_path / "b", id="b", looks="left")).pack.art == -1
    assert load_dir(write_pack(tmp_path / "c", id="c")).turn_s == 0.25 and load_dir(write_pack(tmp_path / "d", id="d", turn=0)).turn_s == 0
    for bad in ("up", "", 1):
        with pytest.raises(ValueError, match="looks"): load_dir(write_pack(tmp_path / "e", id="e", looks=bad))
    for bad in (-1, 99, "slow"):
        with pytest.raises(ValueError, match="turn"): load_dir(write_pack(tmp_path / "f", id="f", turn=bad))


def walking_pet(make, tmp_path):
    p = make("blob", 1.0)
    g = p.screen_geo()
    p.px, p.py, p.vx, p.vy, p.support = g.left + 400.0, floor_y(p), 0.0, 0.0, None
    p.grounded = True; p.enter(State(Motion.WALK)); p.until = float("inf"); p.facing = 1; p.drawn_facing = 1
    return p


def test_turning_round_takes_a_moment_through_edge_on_and_it_does_not_walk_backwards(make, tmp_path):
    p = walking_pet(make, tmp_path)
    for _ in range(3): p.tick()
    x0 = p.px; assert x0 > 400 and p.turn_scale() == 1.0                  # walking right at full width
    p.facing = -1; p.tick()                                                # it decides to go the other way
    assert p.turning() and 0.0 < p.turn_scale() <= 1.0
    seen, xs = [], []
    for _ in range(int(p.defn.turn_s / 0.033) + 1):
        p.tick(); seen.append(p.turn_scale()); xs.append(p.px)
    assert min(abs(v) for v in seen) < 0.35                                 # it passed through (nearly) edge-on
    assert all(a == xs[0] for a in xs[:max(1, len(xs) - 2)])               # standing still while turning: no moonwalking
    for _ in range(4): p.tick()
    assert not p.turning() and p.turn_scale() == -1.0
    x1 = p.px
    for _ in range(10): p.tick()
    assert p.px < x1                                                       # then it walks off to the left, facing left


def test_turn_scale_is_monotonic_from_one_direction_to_the_other(make, tmp_path):
    p = walking_pet(make, tmp_path)
    p.tick(); p.facing = -1; p.tick()
    vals = []
    for _ in range(12):
        p.t += p.defn.turn_s / 10; vals.append(p.turn_scale())
    assert all(a >= b for a, b in zip(vals, vals[1:], strict=False)) and vals[-1] == -1.0 and vals[0] < 1.0


def test_mochi_still_turns_at_once(pet):
    pet.grounded = True; pet.enter(State(Motion.WALK)); pet.until = float("inf"); pet.tick()
    pet.facing = -pet.facing; pet.tick()
    assert not pet.turning() and pet.turn_scale() == float(pet.facing)


def test_the_click_mask_covers_every_stage_of_a_turn(make, tmp_path):
    p = walking_pet(make, tmp_path)
    p.tick(); p.facing = -1; p.tick()
    for k in range(12):
        p.t = p.turn_start + p.defn.turn_s * k / 11
        p.state, p.squash, p.hearts, p.hot = State(Motion.WALK), 0.0, [], False
        left, edge = uncovered_and_clipped(p)
        assert left < 40, (k, left)
