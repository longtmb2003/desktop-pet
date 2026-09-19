from PySide6.QtCore import QSettings

from mochi.settings import Settings


def _qs(path):
    return QSettings(str(path), QSettings.IniFormat)


def test_default_theme(tmp_path):
    assert Settings(_qs(tmp_path / "s.ini")).theme == "Kem"


def test_theme_persists_across_instances(tmp_path):
    Settings(_qs(tmp_path / "s.ini")).theme = "Hồng"
    assert Settings(_qs(tmp_path / "s.ini")).theme == "Hồng"


def test_unknown_stored_theme_falls_back(tmp_path):
    qs = _qs(tmp_path / "s.ini")
    qs.setValue("theme", "does-not-exist"); qs.sync()
    assert Settings(_qs(tmp_path / "s.ini")).theme == "Kem"


def test_defaults_and_persistence_of_typed_settings(tmp_path):
    s = Settings(_qs(tmp_path / "s.ini"))
    assert (s.quiet, s.chase, s.speed, s.focus_min) == (False, True, 1.0, 25)
    s.quiet, s.chase, s.speed, s.focus_min = True, False, 1.5, 50
    s.qs.sync()
    t = Settings(_qs(tmp_path / "s.ini"))
    assert (t.quiet, t.chase, t.speed, t.focus_min) == (True, False, 1.5, 50)     # bools survive the ini round trip as bools


def test_out_of_range_or_garbage_values_are_clamped_or_defaulted(tmp_path):
    qs = _qs(tmp_path / "s.ini")
    for k, v in {"speed": "99", "focus_min": "-5", "activity": "fast", "break_min": "", "quiet": "maybe"}.items(): qs.setValue(k, v)
    qs.sync()
    s = Settings(_qs(tmp_path / "s.ini"))
    assert s.speed == 3.0 and s.focus_min == 1                                    # clamped
    assert s.activity == 1.0 and s.break_min == 5 and s.quiet is False            # unparsable: the default
