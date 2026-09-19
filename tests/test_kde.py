import pytest

from mochi.platform.kde import Bus, parse_windows


def test_parse_valid_and_ordered():
    assert list(parse_windows('[["b",1,2,3,4],["a",5,6,7,8]]').items()) == [("b", (1, 2, 3, 4)), ("a", (5, 6, 7, 8))]


def test_malformed_entries_are_skipped():
    js = '[["a",1,2,3,4],["bad",0,0,-5,10],["s",1,2,"x",4],["short",1,2],[7],5,["nan",1,2,3,NaN],["inf",1,2,3,Infinity],["ok",1.5,2,3,4]]'
    assert parse_windows(js) == {"a": (1, 2, 3, 4), "ok": (1.5, 2, 3, 4)}


@pytest.mark.parametrize("bad", ["not json", "5", "null", '{"a": 1}'])
def test_non_list_payload_is_rejected_whole(bad):
    with pytest.raises((ValueError, TypeError)):
        parse_windows(bad)


def test_bus_forwards_good_payload_and_ignores_bad():
    got = []
    bus = Bus(got.append)
    bus.windows('[["a",1,2,3,4]]')
    bus.windows("not json")
    bus.windows("null")
    assert got == [{"a": (1, 2, 3, 4)}]                       # the bad ones never reach the pet


def test_bad_payload_warnings_are_rate_limited(caplog):
    bus = Bus(lambda w: None)
    with caplog.at_level("WARNING", logger="mochi"):
        for _ in range(50):
            bus.windows("garbage")
    assert len(caplog.records) == 1 and bus.dropped == 49


def test_hostile_numbers_are_skipped_not_fatal():
    assert parse_windows('[["a",1,2,3,' + "9" * 400 + '],["ok",1,2,3,4]]') == {"ok": (1, 2, 3, 4)}   # int too large for float


@pytest.mark.parametrize("payload", ["[" * 200000 + "]" * 200000, "[" * 200000, '["' + "x" * 10_000_000 + '"]'])
def test_bus_never_raises_on_hostile_json(payload):
    got = []
    Bus(got.append).windows(payload)                          # deep nesting can raise RecursionError on older Pythons
    assert all(isinstance(w, dict) for w in got)


def test_fullscreen_flag_reaches_the_pet_and_a_bus_without_a_pet_ignores_it():
    class P: fullscreen = False
    pet = P()
    bus = Bus(lambda w: None, pet)
    bus.fullscreen(True); assert pet.fullscreen is True
    bus.fullscreen(False); assert pet.fullscreen is False
    Bus(lambda w: None).fullscreen(True)                                # no pet yet: harmless
