"""The Settings window. Every control writes to Settings and takes effect immediately; there is no OK/Apply."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QSpinBox, QVBoxLayout

from . import autostart, monitor
from .renderer import THEMES


def _percent_slider(value, on_change, lo=30, hi=300):
    s = QSlider(Qt.Horizontal); s.setRange(lo, hi); s.setValue(round(value * 100))
    label = QLabel(f"{s.value()}%")
    s.valueChanged.connect(lambda v: (label.setText(f"{v}%"), on_change(v / 100)))
    row = QHBoxLayout(); row.addWidget(s); row.addWidget(label)
    return row, s


class SettingsDialog(QDialog):
    def __init__(self, pet):
        super().__init__()
        self.pet, self.cfg = pet, pet.cfg
        self.setWindowTitle("Mochi: Cài đặt")
        lay, form = QVBoxLayout(self), QFormLayout()
        lay.addLayout(form)

        self.who = QComboBox()
        for pid, d in pet.pets.items(): self.who.addItem(d.name, pid)
        self.who.setCurrentIndex(max(0, self.who.findData(pet.defn.id)))
        self.who.currentIndexChanged.connect(lambda _: self.set_pet(self.who.currentData()))
        if len(pet.pets) > 1: form.addRow("Nhân vật", self.who)
        self.theme = QComboBox(); self.theme.addItems(list(THEMES)); self.theme.setCurrentText(pet.theme)
        self.theme.currentTextChanged.connect(pet.set_theme)
        self.theme_row = form.rowCount(); form.addRow("Màu (Mochi)", self.theme)
        row, self.size = _percent_slider(self.cfg.scale, self.set_scale, 60, 200); form.addRow("Kích thước", row)
        row, self.speed = _percent_slider(self.cfg.speed, self.set_speed); form.addRow("Tốc độ đi", row)
        row, self.activity = _percent_slider(self.cfg.activity, self.set_activity); form.addRow("Tần suất hành vi", row)

        self.boxes = {}
        for key, text in (("chase", "Cho phép chạy đuổi theo con trỏ"), ("chatter", "Thỉnh thoảng nói vu vơ"),
                          ("time_of_day", "Theo giờ trong ngày (đêm buồn ngủ hơn)"), ("sound", "Âm thanh (báo hết giờ Pomodoro)"),
                          ("monitor", "Phản ứng khi máy bận (CPU cao)"), ("quiet", "Chế độ yên lặng"),
                          ("quiet_auto", "Tự yên lặng khi có ứng dụng toàn màn hình")):
            self.boxes[key] = self.box(text, getattr(self.cfg, key), lambda on, k=key: self.set_flag(k, on))
            form.addRow(self.boxes[key])
        if not monitor.AVAILABLE:
            self.boxes["monitor"].setEnabled(False)
            self.boxes["monitor"].setToolTip("Cần cài psutil: pip install psutil")
        self.autostart = self.box("Tự chạy khi đăng nhập", autostart.is_enabled(), self.set_autostart)
        form.addRow(self.autostart)

        self.focus = QSpinBox(); self.focus.setRange(1, 180); self.focus.setSuffix(" phút"); self.focus.setValue(self.cfg.focus_min)
        self.focus.valueChanged.connect(lambda v: setattr(self.cfg, "focus_min", v))
        self.rest = QSpinBox(); self.rest.setRange(1, 60); self.rest.setSuffix(" phút"); self.rest.setValue(self.cfg.break_min)
        self.rest.valueChanged.connect(lambda v: setattr(self.cfg, "break_min", v))
        form.addRow("Pomodoro: tập trung", self.focus)
        form.addRow("Pomodoro: nghỉ", self.rest)

        back = QPushButton("Gọi Mochi về / đặt lại vị trí"); back.clicked.connect(pet.bring_back)
        lay.addWidget(back)
        self.back = back

    @staticmethod
    def box(text, on, slot):
        b = QCheckBox(text); b.setChecked(bool(on)); b.toggled.connect(slot)
        return b

    @staticmethod
    def set_autostart(on):
        autostart.enable() if on else autostart.disable()

    def set_pet(self, pid):
        self.cfg.pet = pid
        self.pet.apply_settings()

    def set_scale(self, v):
        self.cfg.scale = v                                        # dragging the slider resizes live
        self.pet.apply_settings()

    def set_speed(self, v):
        self.cfg.speed = v

    def set_activity(self, v):
        self.cfg.activity = v

    def set_flag(self, key, on):
        setattr(self.cfg, key, on)
        self.pet.apply_settings()
