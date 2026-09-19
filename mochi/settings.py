"""Persistent user settings, stored with QSettings."""
from PySide6.QtCore import QSettings

from .renderer import THEMES


class Settings:
    def __init__(self, qs=None):
        self.qs = qs or QSettings("mochi-pet", "mochi")

    @property
    def theme(self):
        t = self.qs.value("theme", "Kem")
        return t if t in THEMES else "Kem"

    @theme.setter
    def theme(self, name):
        self.qs.setValue("theme", name)
