"""The Settings window. Every control writes to Settings and takes effect immediately; there is no OK/Apply."""
from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QSpinBox, QVBoxLayout

from . import autostart, modes, monitor
from .renderer import THEMES


def _percent_slider(value, on_change, lo=30, hi=300):
    s = QSlider(Qt.Horizontal); s.setRange(lo, hi); s.setValue(round(value * 100))
    label = QLabel(f"{s.value()}%")
    s.valueChanged.connect(lambda v: (label.setText(f"{v}%"), on_change(v / 100)))
    row = QHBoxLayout(); row.addWidget(s); row.addWidget(label)
    s.label = label
    return row, s


class SettingsDialog(QDialog):
    def __init__(self, pet):
        super().__init__()
        self.pet, self.cfg = pet, pet.cfg
        self.setWindowTitle("Mochi: Cài đặt")
        lay, form = QVBoxLayout(self), QFormLayout()
        lay.addLayout(form)

        self.mode = QComboBox(); self.fill_modes()
        self.mode.currentIndexChanged.connect(lambda _: self.choose_mode(self.mode.currentData()))
        form.addRow("Chế độ", self.mode)
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
                          ("desktop", "Nhận xét về các mục trên màn hình nền"),
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

        rem_btn = QPushButton("Nhắc việc..."); rem_btn.clicked.connect(pet.open_reminders); lay.addWidget(rem_btn)
        back = QPushButton("Gọi Mochi về / đặt lại vị trí"); back.clicked.connect(pet.bring_back)
        lay.addWidget(back)
        self.back = back

    def choose_mode(self, mid):
        self.pet.set_mode(mid)
        self.reload()                                             # its settings replace what the controls show

    def fill_modes(self):
        with QSignalBlocker(self.mode):
            self.mode.clear()
            for mid, m in modes.available(self.cfg.custom_modes).items(): self.mode.addItem(m.name, mid)
            self.mode.setCurrentIndex(max(0, self.mode.findData(self.cfg.mode)))

    def reload(self):
        """show the current settings (a mode was switched, or saved, from the menu while this window was open)"""
        c = self.cfg
        self.fill_modes()
        for w, v in ((self.speed, round(c.speed * 100)), (self.activity, round(c.activity * 100)), (self.size, round(c.scale * 100)),
                     (self.focus, c.focus_min), (self.rest, c.break_min)):
            with QSignalBlocker(w): w.setValue(v)
            if hasattr(w, "label"): w.label.setText(f"{v}%")
        for k, b in self.boxes.items():
            with QSignalBlocker(b): b.setChecked(bool(getattr(c, k)))

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
