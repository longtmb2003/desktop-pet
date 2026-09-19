import json

import pytest

from mochi.pets import MOCHI, available
from mochi.pets.pack import MAX_FRAMES, load_dir, pack_dirs
from mochi.state import Action, Motion

from conftest import write_pack


def test_a_valid_pack_becomes_a_pet_definition(qapp, tmp_path):
    d = load_dir(write_pack(tmp_path / "blob"))
    assert (d.id, d.name, d.kind, d.size, d.feet, d.top, d.height) == ("blob", "Blob", "sprite", 200, 190, 40, 150)
    assert d.walk_speed == 30 and d.chatter == ("Bloop", "Hello") and d.scream == "Waaah!"
    assert d.behaviors == {(Motion.IDLE, Action.NONE): 3, (Motion.WALK, Action.NONE): 2, (Motion.SLEEP, Action.NONE): 1,
                           (Motion.IDLE, Action.RANT): 1}
    assert d.pack.face("neutral", 0) is not d.pack.face("talk", 0)
    assert d.pack.face("sad", 0) is d.pack.face("neutral", 0)                       # an unknown kind falls back to neutral


def test_animated_faces_step_with_time_and_single_frames_do_not(qapp, tmp_path):
    pk = load_dir(write_pack(tmp_path / "blob")).pack
    assert [pk.face("talk", t) is pk.faces["talk"][i] for t, i in ((0.0, 0), (0.11, 1), (0.21, 0), (0.31, 1))] == [True] * 4
    assert pk.face("laugh", 5.0) is pk.faces["laugh"][0]


@pytest.mark.parametrize("over,why", [
    ({"id": "../evil"}, "bad id"), ({"id": ""}, "bad id"), ({"size": 5}, "size"), ({"size": "big"}, "size"),
    ({"size": float("nan")}, "size"),
    ({"feet": 300}, "feet"), ({"height": 195}, "feet"), ({"body": "nope.png"}, "cannot read"), ({"body": "../body.png"}, "outside"),
    ({"body": "/etc/passwd"}, "outside"), ({"face": {"box": [0, 0, 1000, 1000]}}, "outside the body"), ({"face": {}}, "face.box"),
    ({"faces": {}}, "neutral"), ({"faces": {"neutral": []}}, "neutral"),
    ({"faces": {"neutral": ["faces/n.png"], "talk": ["faces/nope.png"]}}, "cannot read"),
    ({"faces": {"neutral": ["faces/n.png"] * (MAX_FRAMES + 1)}}, "images"), ({"behaviors": {"idle": 1}}, "at least one more"),
    ({"behaviors": {"walk": 1, "sleep": 1}}, '"idle"'), ({"behaviors": {"idle": 1, "fly": 1}}, "unknown behaviour"),
    ({"behaviors": {"idle": 1, "walk": -1}}, "behaviors.walk"), ({"fps": {"talk": 0}}, "fps"), ({"walk_speed": 1e9}, "walk_speed"),
])
def test_bad_packs_are_refused_with_a_reason(qapp, tmp_path, over, why):
    with pytest.raises(ValueError, match=why):
        load_dir(write_pack(tmp_path / "bad", **over))


def test_a_symlink_out_of_the_pack_is_refused(qapp, tmp_path):
    root = write_pack(tmp_path / "blob")
    (tmp_path / "secret.png").write_bytes((root / "body.png").read_bytes())
    (root / "link.png").symlink_to(tmp_path / "secret.png")
    with pytest.raises(ValueError, match="outside"):
        load_dir(write_pack(tmp_path / "blob", body="link.png"))


def test_junk_json_and_huge_files_are_refused(qapp, tmp_path):
    root = write_pack(tmp_path / "blob")
    for text, exc in (("not json", ValueError), ("[1, 2]", ValueError), ('{"id": "x"}', ValueError)):
        (root / "pack.json").write_text(text)
        with pytest.raises(exc): load_dir(root)
    (root / "pack.json").write_text(json.dumps({"id": "x", "pad": "y" * 70_000}))
    with pytest.raises(ValueError, match="too large"): load_dir(root)


def test_text_from_a_pack_is_sanitised_and_bounded(qapp, tmp_path):
    d = load_dir(write_pack(tmp_path / "blob", name="Bl\x00ob\n" + "x" * 100, scream="Á\n" * 50,
                            chatter=["a\x1b[0m b", "", 5, "x" * 999] + ["m"] * 100))
    assert "\x00" not in d.name and len(d.name) <= 40
    assert d.chatter[0] == "a [0m b" and len(d.chatter) <= 50 and all(len(c) <= 200 and c.isprintable() for c in d.chatter)
    assert len(d.scream) <= 20


def test_available_lists_mochi_first_and_skips_broken_or_clashing_packs(qapp, tmp_path, caplog, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "nowhere"))
    write_pack(tmp_path / "packs" / "good")
    write_pack(tmp_path / "packs" / "broken", body="missing.png", id="broken")
    write_pack(tmp_path / "packs" / "clash", id="mochi")
    (tmp_path / "packs" / "empty").mkdir()
    pets = available([tmp_path / "packs"])
    assert "mochi" in pets and pets["mochi"] is MOCHI and "blob" in pets and "broken" not in pets
    assert sum("skipping pet pack" in r.message for r in caplog.records) == 2       # the broken one and the id clash, warned not fatal


def test_pack_dirs_finds_user_packs_under_xdg_data_home(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    write_pack(tmp_path / "mochi-pet" / "pets" / "mine")
    assert any(d.name == "mine" for d in pack_dirs())


def test_mochi_keeps_the_original_geometry_and_behaviour():
    assert (MOCHI.size, MOCHI.feet, MOCHI.top, MOCHI.height, MOCHI.walk_speed) == (160, 146, 40, 106, 55.0)
