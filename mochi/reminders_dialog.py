"""The window for setting up reminders. Every change is saved and applied at once."""
from PySide6.QtCore import QTime
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton,
                               QSpinBox, QTimeEdit, QVBoxLayout, QWidget)

from . import reminders as rem

DAYS = ("T2", "T3", "T4", "T5", "T6", "T7", "CN")


class RemindersDialog(QDialog):
    def __init__(self, pet):
        super().__init__()
        self.pet, self.items = pet, rem.parse(pet.cfg.reminders)
        self.setWindowTitle("Mochi: Nhắc việc")
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Mochi sẽ nói câu nhắc bằng bong bóng thoại (kèm tiếng chuông nếu bật âm thanh)."))
        self.list = QListWidget(); lay.addWidget(self.list)

        form = QFormLayout(); lay.addLayout(form)
        self.text = QLineEdit(); self.text.setPlaceholderText("Ví dụ: Uống nước đi!"); self.text.setMaxLength(rem.MAX_TEXT)
        self.kind = QComboBox(); self.kind.addItem("Lặp lại sau mỗi ... phút", "every"); self.kind.addItem("Hằng ngày vào lúc ...", "daily")
        self.minutes = QSpinBox(); self.minutes.setRange(1, 1440); self.minutes.setValue(45); self.minutes.setSuffix(" phút")
        self.at = QTimeEdit(QTime(9, 0)); self.at.setDisplayFormat("HH:mm")
        self.days = [QCheckBox(d) for d in DAYS]
        for b in self.days: b.setChecked(True)
        row = QHBoxLayout(); [row.addWidget(b) for b in self.days]
        self.days_row = QWidget(); self.days_row.setLayout(row); row.setContentsMargins(0, 0, 0, 0)
        self.enabled = QCheckBox("Đang bật"); self.enabled.setChecked(True)
        form.addRow("Nội dung", self.text); form.addRow("Khi nào", self.kind); form.addRow("Mỗi", self.minutes)
        form.addRow("Lúc", self.at); form.addRow("Các ngày", self.days_row); form.addRow(self.enabled)

        buttons = QHBoxLayout(); lay.addLayout(buttons)
        self.add, self.update_btn, self.delete, self.test = (QPushButton(t) for t in ("Thêm", "Cập nhật", "Xoá", "Thử ngay"))
        for b in (self.add, self.update_btn, self.delete, self.test): buttons.addWidget(b)
        self.status = QLabel(""); lay.addWidget(self.status)

        self.kind.currentIndexChanged.connect(lambda _: self.show_kind())
        self.list.currentRowChanged.connect(self.load_row)
        self.add.clicked.connect(self.on_add); self.update_btn.clicked.connect(self.on_update)
        self.delete.clicked.connect(self.on_delete); self.test.clicked.connect(self.on_test)
        self.refresh(); self.show_kind()

    # ---- the form <-> a Reminder ------------------------------------------------------------------------
    def show_kind(self):
        daily = self.kind.currentData() == "daily"
        self.minutes.setVisible(not daily); self.at.setVisible(daily); self.days_row.setVisible(daily)

    def from_form(self):
        """the Reminder the form describes, or None (with a message) if it isn't usable yet"""
        days = tuple(i for i, b in enumerate(self.days) if b.isChecked())
        try:
            return rem.from_dict({"text": self.text.text(), "kind": self.kind.currentData(), "minutes": self.minutes.value(),
                                  "at": self.at.time().toString("HH:mm"), "days": days, "enabled": self.enabled.isChecked()})
        except ValueError as e:
            msgs = {"empty text": "Hãy nhập nội dung nhắc.", "days must be a list of 0-6": "Chọn ít nhất một ngày."}
            self.status.setText(msgs.get(str(e), str(e)))
            return None

    def load_row(self, row):
        if not 0 <= row < len(self.items): return
        r = self.items[row]
        self.text.setText(r.text); self.kind.setCurrentIndex(self.kind.findData(r.kind)); self.minutes.setValue(r.minutes)
        self.at.setTime(QTime.fromString(r.at, "HH:mm")); self.enabled.setChecked(r.enabled)
        for i, b in enumerate(self.days): b.setChecked(i in r.days)

    # ---- actions ------------------------------------------------------------------------------------------
    def save(self):
        self.pet.cfg.reminders = rem.dump(self.items)
        self.pet.apply_settings()

    def refresh(self, select=None):
        self.list.blockSignals(True)
        self.list.clear(); self.list.addItems([r.describe() for r in self.items])
        if select is not None: self.list.setCurrentRow(select)
        self.list.blockSignals(False)
        self.status.setText(f"{len(self.items)}/{rem.MAX_REMINDERS} nhắc việc")

    def on_add(self):
        r = self.from_form()
        if r is None: return
        if len(self.items) >= rem.MAX_REMINDERS:
            self.status.setText(f"Tối đa {rem.MAX_REMINDERS} nhắc việc."); return
        self.items.append(r); self.save(); self.refresh(len(self.items) - 1)

    def on_update(self):
        row, r = self.list.currentRow(), self.from_form()
        if r is None or not 0 <= row < len(self.items): return
        self.items[row] = r; self.save(); self.refresh(row)

    def on_delete(self):
        row = self.list.currentRow()
        if not 0 <= row < len(self.items): return
        del self.items[row]; self.save(); self.refresh(min(row, len(self.items) - 1) if self.items else None)

    def on_test(self):
        r = self.from_form()
        if r is not None: self.pet.remind(r)
