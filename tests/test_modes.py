import json

import pytest

from mochi import modes
from mochi.state import BEHAVIORS, Action, Motion


def test_every_builtin_sets_every_key_within_range():
    assert list(modes.BUILTIN) == ["normal", "work", "play", "sleep", "quiet"]
    for m in modes.BUILTIN.values():
        assert set(m.values) == set(modes.KEYS) and m.builtin
        assert modes.clean_values(m.values) == m.values                       # already clean
    assert modes.BUILTIN["normal"].values == modes.DEFAULTS
    assert modes.BUILTIN["quiet"].values["quiet"] is True and modes.BUILTIN["play"].values["chase"] is True
    assert modes.BUILTIN["work"].values["chase"] is False and modes.BUILTIN["work"].stay == "work"
    assert modes.BUILTIN["sleep"].stay == "sleep"


def test_values_from_junk_are_cleaned_field_by_field():
    got = modes.clean_values({"activity": 99, "speed": -1, "chase": "yes", "chatter": False, "sound": None, "quiet": 1, "extra": 5,
                             "time_of_day": True})
    assert got == {"activity": 3.0, "speed": 0.3, "chase": True, "chatter": False, "time_of_day": True, "sound": True, "quiet": False,
                   "mischief": True}
    assert modes.clean_values(None) == modes.DEFAULTS and modes.clean_values({"speed": float("nan")})["speed"] == 1.0
    assert modes.clean_values({"activity": True})["activity"] == 1.0            # a bool is not a number here


def test_custom_modes_round_trip_and_survive_junk():
    m = modes.make("custom:Của tôi", "Của tôi", stay="work", boost={"chase": 3.0}, builtin=False, speed=1.7, chase=False)
    raw = modes.dump_custom({m.id: m, **modes.BUILTIN})                          # built-ins are never written out
    got = modes.parse_custom(raw)
    assert list(got) == ["custom:Của tôi"] and got["custom:Của tôi"].values["speed"] == 1.7 and got["custom:Của tôi"].stay == "work"
    assert got["custom:Của tôi"].boost == {"chase": 3.0} and not got["custom:Của tôi"].builtin
    bad = '{"a": {"stay": "fly", "boost": {"nope": 2, "idle": true, "walk": 999}}}'
    for junk in ("", "not json", "[]", "null", '{"": {}}', '{"x": 5}', bad):
        r = modes.parse_custom(junk)
        assert all(x.stay in ("", "sleep", "work") and set(x.boost) <= set(modes.BEHAVIOR_NAMES) and x.boost.get("idle") is None and
                   x.boost.get("walk") is None for x in r.values())
    assert len(modes.parse_custom(json.dumps({f"m{i}": {} for i in range(50)}))) == modes.MAX_CUSTOM
    assert list(modes.parse_custom(json.dumps({"a\x00b\n" + "x" * 99: {}}))) == ["custom:a b " + "x" * 26]


def test_available_lists_builtin_first_and_a_custom_cannot_shadow_one():
    got = modes.available(json.dumps({"normal": {"values": {"speed": 2.0}}}))
    assert list(got)[:5] == list(modes.BUILTIN) and got["normal"] is modes.BUILTIN["normal"]     # id is "custom:normal", not "normal"
    assert "custom:normal" in got


def test_snapshot_keeps_the_current_values_and_inherits_the_active_modes_leanings():
    cur = {**modes.DEFAULTS, "speed": 1.4, "chatter": False}
    m = modes.snapshot("  Họp  ", cur, modes.BUILTIN["play"])
    assert (m.id, m.name, m.values["speed"], m.values["chatter"], m.boost, m.stay, m.builtin) == \
        ("custom:Họp", "Họp", 1.4, False, {"chase": 4, "walk": 2}, "", False)
    assert modes.snapshot("x", cur).boost == {}
    with pytest.raises(ValueError): modes.snapshot("  \n ", cur)


def test_boosting_weights_multiplies_only_the_named_behaviours_and_leaves_the_original_alone():
    orig = dict(BEHAVIORS)
    w = modes.weights(BEHAVIORS, {"chase": 4, "idle": 2})
    assert w[(Motion.WALK, Action.CHASE)] == 4 * BEHAVIORS[(Motion.WALK, Action.CHASE)]
    assert w[(Motion.IDLE, Action.NONE)] == 2 * BEHAVIORS[(Motion.IDLE, Action.NONE)]
    assert w[(Motion.WALK, Action.NONE)] == BEHAVIORS[(Motion.WALK, Action.NONE)]
    assert BEHAVIORS == orig and modes.weights(BEHAVIORS, {}) is BEHAVIORS
