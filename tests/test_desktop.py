import os

import pytest

from mochi import desktop


@pytest.fixture
def desk(tmp_path):
    (tmp_path / "Ghi chú.txt").write_text("x")
    (tmp_path / ".hidden").write_text("x")
    (tmp_path / ".directory").write_text("[Desktop Entry]\nIcon=x\n")
    (tmp_path / "Dự án").mkdir()
    (tmp_path / "tele.desktop").write_text("[Desktop Entry]\nName[vi]=Sai\nName=Telegram Desktop\nExec=telegram\n"
                                           "[Desktop Action x]\nName=Khác\n")
    return tmp_path


def test_items_are_the_visible_things_sorted_with_friendly_names(desk):
    got = desktop.items(desk)
    assert [n for _, n in got] == ["Dự án", "Ghi chú", "Telegram Desktop"]
    assert all(p.parent == desk for p, _ in got) and not any(p.name.startswith(".") for p, _ in got)


def test_a_launcher_is_named_from_its_desktop_entry_and_a_broken_one_from_its_file_name(tmp_path):
    (tmp_path / "a.desktop").write_text("[Desktop Action x]\nName=Sai nhóm\n[Desktop Entry]\nName=Đúng\n")
    (tmp_path / "b.desktop").write_bytes(b"\xff\xfe\x00garbage")
    (tmp_path / "c.desktop").write_text("[Desktop Entry]\nName=\n")
    (tmp_path / "d.desktop").write_text("[Desktop Entry]\nName=" + "x" * 500 + "\n")
    assert desktop.entry_name(tmp_path / "a.desktop") == "Đúng"                # the Name of [Desktop Entry], not of an action
    assert desktop.entry_name(tmp_path / "b.desktop") == "b" and desktop.entry_name(tmp_path / "c.desktop") == "c"
    assert len(desktop.entry_name(tmp_path / "d.desktop")) == desktop.MAX_NAME
    assert desktop.entry_name(tmp_path / "nope.desktop") == "nope"


def test_names_are_sanitised(tmp_path):
    f = tmp_path / "x.desktop"; f.write_text("[Desktop Entry]\nName=a\x1b[31m b\tc\n")
    assert desktop.entry_name(f) == "a [31m b c"


def test_a_symlink_to_a_launcher_reads_the_launcher(tmp_path):
    real = tmp_path / "real"; real.mkdir()
    (real / "org.app.desktop").write_text("[Desktop Entry]\nName=Ứng dụng\n")
    desk = tmp_path / "desk"; desk.mkdir()
    (desk / "org.app.desktop").symlink_to(real / "org.app.desktop")
    assert [n for _, n in desktop.items(desk)] == ["Ứng dụng"]


def test_missing_or_unreadable_folders_and_huge_ones_are_harmless(tmp_path):
    assert desktop.items(tmp_path / "nowhere") == []
    big = tmp_path / "big"; big.mkdir()
    for i in range(desktop.MAX_ITEMS + 30): (big / f"f{i:04d}").write_text("")
    assert len(desktop.items(big)) == desktop.MAX_ITEMS


def test_summary_of_dropped_names():
    assert desktop.summary(["báo cáo.pdf"]) == "báo cáo.pdf" and desktop.summary(["a", "b", "c"]) == "3 thứ"
    assert desktop.summary([]) == "cái gì đó" and desktop.summary(["\x00", "  "]) == "cái gì đó"
    assert len(desktop.summary(["x" * 999])) == desktop.MAX_NAME


def test_the_desktop_folder_can_be_overridden_and_defaults_to_something(monkeypatch, tmp_path):
    monkeypatch.setenv("MOCHI_DESKTOP", str(tmp_path))
    assert desktop.desktop_dir() == tmp_path
    monkeypatch.delenv("MOCHI_DESKTOP")
    assert str(desktop.desktop_dir()) not in ("", ".") and os.path.isabs(str(desktop.desktop_dir()))
