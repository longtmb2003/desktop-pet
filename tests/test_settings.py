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
