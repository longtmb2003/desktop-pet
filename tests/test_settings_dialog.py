import pytest

import mochi.settings_dialog as sd
from mochi.settings_dialog import SettingsDialog
from mochi.state import Motion, State


@pytest.fixture
def dlg(pet, monkeypatch):
    calls = []
    monkeypatch.setattr(sd.autostart, "enable", lambda: calls.append("on"))
    monkeypatch.setattr(sd.autostart, "disable", lambda: calls.append("off"))
    monkeypatch.setattr(sd.autostart, "is_enabled", lambda: False)
    d = SettingsDialog(pet); d.calls = calls
    yield d
    d.close()


def test_it_shows_the_current_values(dlg, pet):
    assert dlg.theme.currentText() == pet.theme and dlg.speed.value() == 100 and dlg.activity.value() == 100
    assert (dlg.focus.value(), dlg.rest.value()) == (25, 5)
    assert dlg.boxes["chase"].isChecked() and not dlg.boxes["quiet"].isChecked() and dlg.boxes["quiet_auto"].isChecked()


def test_changes_are_saved_immediately_and_persist(dlg, pet):
    dlg.speed.setValue(150); dlg.activity.setValue(50)
    dlg.boxes["chase"].setChecked(False); dlg.boxes["sound"].setChecked(False); dlg.boxes["quiet"].setChecked(True)
    dlg.focus.setValue(50); dlg.rest.setValue(10)
    dlg.theme.setCurrentText("Hồng")
    pet.cfg.qs.sync()
    from PySide6.QtCore import QSettings

    from mochi.settings import Settings
    fresh = Settings(QSettings(pet.cfg.qs.fileName(), QSettings.IniFormat))
    assert (fresh.speed, fresh.activity, fresh.chase, fresh.sound, fresh.quiet) == (1.5, 0.5, False, False, True)
    assert (fresh.focus_min, fresh.break_min, fresh.theme) == (50, 10, "Hồng") and pet.theme == "Hồng"


def test_quiet_mode_takes_effect_on_the_running_pet(dlg, pet):
    pet.enter(State()); pet.grounded = True
    dlg.boxes["quiet"].setChecked(True)
    assert pet.quiet and pet.timer.interval() == 50                      # resting pet, quiet: lower frame rate at once
    dlg.boxes["quiet"].setChecked(False)
    assert not pet.quiet and pet.timer.interval() == 33


def test_the_monitor_checkbox_is_disabled_without_psutil(pet, monkeypatch):
    monkeypatch.setattr(sd.monitor, "AVAILABLE", False)
    d = SettingsDialog(pet)
    assert not d.boxes["monitor"].isEnabled() and "psutil" in d.boxes["monitor"].toolTip()
    d.close()


def test_autostart_box_and_bring_back_button(dlg, pet):
    dlg.autostart.setChecked(True); dlg.autostart.setChecked(False)
    assert dlg.calls == ["on", "off"]
    pet.px, pet.py = -9999, 99999
    dlg.back.click()
    assert pet.state.motion is Motion.AIRBORNE and pet.px > -1000


def test_the_pet_opens_one_dialog_and_reuses_it(pet):
    pet.open_settings(); first = pet.dialog
    pet.open_settings()
    assert pet.dialog is first and first.isVisible()
    pet.close()
    assert not first.isVisible()
