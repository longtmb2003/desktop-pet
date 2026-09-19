import pytest
from conftest import write_pack
from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent

import mochi.pet as mp
from mochi.pets import MOCHI
from mochi.pets.pack import load_dir
from mochi.state import Expression, Motion, State


@pytest.fixture
def desk(tmp_path, monkeypatch):
    d = tmp_path / "desktop"; d.mkdir()
    (d / "Báo cáo.pdf").write_text("x")
    (d / "tele.desktop").write_text("[Desktop Entry]\nName=Telegram Desktop\n")
    monkeypatch.setenv("MOCHI_DESKTOP", str(d))
    return d


def drop(pet, *paths):
    mime = QMimeData(); mime.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
    pet.dropEvent(QDropEvent(QPointF(50, 50), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier))


def test_the_pet_accepts_drops_of_files_and_only_files(pet):
    assert pet.acceptDrops()
    from PySide6.QtGui import QDragEnterEvent
    def enter(mime):
        e = QDragEnterEvent(pet.rect().center(), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
        pet.dragEnterEvent(e)
        return e.isAccepted()
    files, text = QMimeData(), QMimeData()
    files.setUrls([QUrl.fromLocalFile("/tmp/x")]); text.setText("hello")
    assert enter(files) and not enter(text)


def test_dropping_a_file_makes_it_react_and_touches_nothing(pet, desk):
    pet.grounded = True; pet.enter(State()); pet.vy = 0.0
    drop(pet, desk / "Báo cáo.pdf")
    assert pet.bubble.lines == "Nom nom! Báo cáo.pdf ngon quá!" and pet.state.expression is Expression.HAPPY and pet.vy < 0 and pet.hearts
    assert (desk / "Báo cáo.pdf").exists()                                       # it never opens, moves or deletes what it is given


def test_dropping_several_files_or_odd_names_is_summarised_and_safe(pet, desk):
    drop(pet, desk / "a", desk / "b", desk / "c")
    assert pet.bubble.lines == "Nom nom! 3 thứ ngon quá!"
    pet.bubble.dismiss(); pet.react_to_drop(["\x00", "\x1b"]); assert pet.bubble.lines == "Nom nom! cái gì đó ngon quá!"
    pet.bubble.dismiss(); pet.react_to_drop(["{name} {0} %s"]); assert "{0} %s" in pet.bubble.lines           # braces are just text
    pet.bubble.dismiss(); drop(pet, *[desk / f"f{i}" for i in range(500)]); assert pet.bubble.isVisible()


def test_a_character_can_have_its_own_drop_line(qapp, tmp_path):
    d = load_dir(write_pack(tmp_path / "p", drop="Cái gì đây? {name}", desktop_remark="Thấy {name} rồi đó"))
    assert (d.drop, d.desktop_remark) == ("Cái gì đây? {name}", "Thấy {name} rồi đó")
    plain = load_dir(write_pack(tmp_path / "q", id="plain"))
    assert plain.drop == MOCHI.drop and plain.desktop_remark == MOCHI.desktop_remark                  # defaults when a pack says nothing
    long = load_dir(write_pack(tmp_path / "r", id="long", drop="x" * 999 + "\x00\n"))
    assert len(long.drop) <= 80 and "\x00" not in long.drop


def test_it_sometimes_remarks_on_desktop_items_and_the_setting_turns_that_off(pet, desk, monkeypatch):
    monkeypatch.setattr(mp.random, "random", lambda: 0.1)                          # the remark branch
    monkeypatch.setattr(mp.random, "choice", lambda seq: seq[-1] if isinstance(seq, list) else seq[0])
    assert pet.idle_remark() == "Telegram Desktop nằm đó lâu rồi nhỉ?"
    pet.cfg.desktop = False
    assert pet.idle_remark() in MOCHI.chatter
    pet.cfg.desktop = True; monkeypatch.setattr(mp.random, "random", lambda: 0.9)
    assert pet.idle_remark() in MOCHI.chatter                                     # usually its own chatter


def test_remarks_are_quiet_when_quiet(pet, desk):
    pet.grounded = True; pet.enter(State()); pet.next_chat = 0.0; pet.cfg.quiet = True
    pet.py = pet.screen_geo().bottom + 1 - pet.feet
    pet.tick()
    assert not pet.bubble.isVisible()


def test_the_list_follows_the_folder(pet, desk):
    assert [n for _, n in pet.desktop_items()] == ["Báo cáo", "Telegram Desktop"]
    assert str(desk) in pet.desk_watch.directories()
    (desk / "Mới.txt").write_text("x")
    pet.desk_items = None                                                          # what the folder watcher does on a change
    assert "Mới" in [n for _, n in pet.desktop_items()]
    pet.desk_watch.directoryChanged.emit(str(desk))
    assert pet.desk_items is None


def test_dropping_on_a_sleeping_pet_wakes_it_and_a_falling_one_just_speaks(pet, desk):
    pet.grounded = True; pet.enter(State(Motion.SLEEP)); drop(pet, desk / "a")
    assert pet.state.expression is Expression.HAPPY
    pet.enter(State(Motion.AIRBORNE)); pet.grounded = False; drop(pet, desk / "a")
    assert pet.state == State(Motion.AIRBORNE) and pet.bubble.isVisible()
