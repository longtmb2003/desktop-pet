import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")     # before any Qt import: tests never touch the real desktop

import pytest  # noqa: E402
from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from mochi.pet import Pet  # noqa: E402
from mochi.settings import Settings  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pet(qapp, tmp_path):
    p = Pet(Settings(QSettings(str(tmp_path / "mochi.ini"), QSettings.IniFormat)))
    p.timer.stop()                                          # tests drive tick() by hand
    p.clock.restart = lambda: 33                            # fixed 33 ms frames
    yield p
    p.close()
