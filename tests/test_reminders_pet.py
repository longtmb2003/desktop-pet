import pytest
from conftest import write_pack  # noqa: F401  (keeps conftest imported first)
from PySide6.QtCore import QSettings

import mochi.pet as mp
from mochi import reminders as rem
from mochi.reminders_dialog import RemindersDialog
from mochi.settings import Settings
from mochi.state import Motion, State


@pytest.fixture
def chimes(monkeypatch):
    got = []
    monkeypatch.setattr(mp, "chime", lambda: got.append(1))
    return got


def set_reminders(pet, *rs):
    pet.cfg.reminders = rem.dump(list(rs))
    pet.apply_settings()


def test_a_due_reminder_is_said_with_a_hop_and_a_chime(pet, chimes):
    pet.grounded = True; pet.enter(State()); pet.vy = 0.0
    pet.remind(rem.Reminder("Uống nước đi!"))
    assert pet.bubble.lines == "Nhắc: Uống nước đi!" and pet.vy < 0 and chimes == [1]


def test_quiet_mode_and_mute_silence_the_chime_but_not_the_words(pet, chimes):
    pet.grounded = True; pet.enter(State())
    pet.cfg.quiet = True
    pet.remind(rem.Reminder("Họp"))
    assert pet.bubble.isVisible() and chimes == []
    pet.bubble.dismiss(); pet.cfg.quiet, pet.cfg.sound = False, False
    pet.remind(rem.Reminder("Họp")); assert pet.bubble.isVisible() and chimes == []


def test_the_pet_checks_the_schedule_once_a_second_and_speaks_when_something_is_due(pet, chimes):
    t = [1000.0]
    pet.sched.mono = lambda: t[0]                                                 # a clock we control
    set_reminders(pet, rem.Reminder("Đứng dậy", "every", 30))
    pet.grounded = True; pet.enter(State()); pet.until = float("inf")
    pet.tick(); assert not pet.bubble.isVisible()
    t[0] += 30 * 60 + 1; pet.next_check = 0.0
    pet.tick()
    assert pet.bubble.lines == "Nhắc: Đứng dậy"
    pet.bubble.dismiss(); pet.next_check = 0.0; pet.tick(); assert not pet.bubble.isVisible()          # said once


def test_the_check_is_not_done_every_frame(pet):
    calls = []
    pet.sched.due = lambda: calls.append(1) or []
    pet.enter(State(Motion.IDLE)); pet.until = float("inf")
    for _ in range(90): pet.tick()                                                # ~3 seconds of 33 ms frames
    assert 2 <= len(calls) <= 5


def test_reminders_wait_for_a_fullscreen_app_to_finish_when_auto_quiet_is_on(pet, chimes):
    pet.fullscreen = True
    pet.sched.due = lambda: [rem.Reminder("Họp")]
    pet.check_reminders()
    assert not pet.bubble.isVisible() and len(pet.pending) == 1
    pet.sched.due = lambda: []
    pet.fullscreen = False; pet.check_reminders()
    assert pet.bubble.lines == "Nhắc: Họp" and pet.pending == []
    pet.cfg.quiet_auto = False; pet.fullscreen = True; pet.bubble.dismiss()      # auto-quiet switched off: fullscreen doesn't hold them
    pet.sched.due = lambda: [rem.Reminder("Nghỉ")]; pet.check_reminders()
    assert pet.bubble.lines == "Nhắc: Nghỉ"


def test_editing_the_list_reaches_the_running_scheduler_and_keeps_untouched_ones_on_schedule(pet):
    a = rem.Reminder("a", "every", 10)
    set_reminders(pet, a)
    assert pet.sched.items == [a]
    before = dict(pet.sched.state[a])
    set_reminders(pet, a, rem.Reminder("b", "every", 5))
    assert [r.text for r in pet.sched.items] == ["a", "b"] and pet.sched.state[a] == before
    set_reminders(pet)
    assert pet.sched.items == []


def test_a_corrupt_setting_gives_no_reminders_instead_of_a_crash(qapp, tmp_path):
    qs = QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat); qs.setValue("reminders", "{{{not json"); qs.sync()
    cfg = Settings(QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat))
    p = mp.Pet(cfg, {"mochi": mp.MOCHI}); p.timer.stop()
    assert p.sched.items == []
    p.close()


# ---- the dialog ---------------------------------------------------------------------------------------------
@pytest.fixture
def dlg(pet):
    d = RemindersDialog(pet)
    yield d
    d.close()


def test_adding_an_interval_reminder_saves_and_applies_it(dlg, pet):
    dlg.text.setText("Uống nước đi!"); dlg.minutes.setValue(30)
    dlg.add.click()
    assert rem.parse(pet.cfg.reminders) == [rem.Reminder("Uống nước đi!", "every", 30)]
    assert pet.sched.items == rem.parse(pet.cfg.reminders) and dlg.list.count() == 1 and "mỗi 30 phút" in dlg.list.item(0).text()


def test_adding_a_daily_reminder_with_chosen_days(dlg, pet):
    from PySide6.QtCore import QTime
    dlg.text.setText("Họp nhóm"); dlg.kind.setCurrentIndex(dlg.kind.findData("daily")); dlg.at.setTime(QTime(9, 30))
    for i in (5, 6): dlg.days[i].setChecked(False)                               # not at the weekend
    dlg.add.click()
    r = rem.parse(pet.cfg.reminders)[0]
    assert (r.kind, r.at, r.days) == ("daily", "09:30", (0, 1, 2, 3, 4))
    assert not dlg.minutes.isVisibleTo(dlg) and dlg.at.isVisibleTo(dlg) and dlg.days_row.isVisibleTo(dlg)


def test_an_empty_text_or_no_days_is_refused_with_a_message(dlg, pet):
    dlg.add.click()
    assert pet.cfg.reminders == "" and "nội dung" in dlg.status.text()
    dlg.text.setText("x"); dlg.kind.setCurrentIndex(dlg.kind.findData("daily"))
    for b in dlg.days: b.setChecked(False)
    dlg.add.click()
    assert pet.cfg.reminders == "" and "ngày" in dlg.status.text()


def test_selecting_editing_and_deleting(dlg, pet):
    for t in ("một", "hai", "ba"):
        dlg.text.setText(t); dlg.add.click()
    dlg.list.setCurrentRow(1)
    assert dlg.text.text() == "hai"                                              # the form shows the selected reminder
    dlg.text.setText("hai sửa"); dlg.enabled.setChecked(False); dlg.update_btn.click()
    assert [r.text for r in rem.parse(pet.cfg.reminders)] == ["một", "hai sửa", "ba"] and not rem.parse(pet.cfg.reminders)[1].enabled
    dlg.delete.click()
    assert [r.text for r in rem.parse(pet.cfg.reminders)] == ["một", "ba"] and dlg.list.count() == 2
    dlg.list.setCurrentRow(-1); dlg.delete.click(); dlg.update_btn.click()          # nothing selected: harmless
    assert dlg.list.count() == 2


def test_the_list_is_capped(dlg, pet):
    for i in range(rem.MAX_REMINDERS + 3):
        dlg.text.setText(f"r{i}"); dlg.add.click()
    assert len(rem.parse(pet.cfg.reminders)) == rem.MAX_REMINDERS and "Tối đa" in dlg.status.text()


def test_test_now_speaks_without_saving_anything(dlg, pet, chimes):
    pet.grounded = True; pet.enter(State())
    dlg.text.setText("Thử xem"); dlg.test.click()
    assert pet.bubble.lines == "Nhắc: Thử xem" and pet.cfg.reminders == ""


def test_the_menu_and_settings_open_the_same_dialog(pet):
    assert "Nhắc việc..." in [a.text() for a in pet.build_menu().actions()]
    pet.open_reminders(); first = pet.reminders_dialog
    pet.open_reminders()
    assert pet.reminders_dialog is first and first.isVisible()
    pet.close()
    assert not first.isVisible()
