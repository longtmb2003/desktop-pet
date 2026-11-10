"""Catppuccin dark minimalist theme (QSS) for Mochi dialogs and widgets."""

CATPPUCCIN_STYLE = """
/* Global Window / Dialog Style */
QDialog {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

QWidget {
    color: #cdd6f4;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

/* Labels */
QLabel {
    color: #cdd6f4;
    font-size: 13px;
    padding: 1px 0px;
}

/* Inputs, ComboBox, SpinBox, TimeEdit */
QLineEdit, QComboBox, QSpinBox, QTimeEdit {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 8px;
    padding: 6px 10px;
    selection-background-color: #b4befe;
    selection-color: #1e1e2e;
}

QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QTimeEdit:hover {
    border: 1px solid #45475a;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTimeEdit:focus {
    border: 1px solid #b4befe;
    background-color: #1e1e2e;
}

/* ComboBox dropdown */
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: none;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
}

QComboBox::down-arrow {
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #a6adc8;
    margin-right: 6px;
}

QComboBox QAbstractItemView {
    background-color: #181825;
    border: 1px solid #45475a;
    border-radius: 8px;
    color: #cdd6f4;
    selection-background-color: #313244;
    selection-color: #b4befe;
    padding: 4px;
    outline: none;
}

/* Buttons */
QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 8px;
    padding: 7px 16px;
    font-weight: 500;
    min-height: 18px;
}

QPushButton:hover {
    background-color: #45475a;
    border-color: #585b70;
    color: #f5e0dc;
}

QPushButton:pressed {
    background-color: #585b70;
    border-color: #b4befe;
}

QPushButton:disabled {
    background-color: #181825;
    color: #6c7086;
    border-color: #313244;
}

QPushButton[primary="true"] {
    background-color: #b4befe;
    color: #1e1e2e;
    border: 1px solid #b4befe;
    font-weight: 600;
}

QPushButton[primary="true"]:hover {
    background-color: #cba6f7;
    border-color: #cba6f7;
}

QPushButton[primary="true"]:pressed {
    background-color: #89b4fa;
    border-color: #89b4fa;
}

/* List Widget (Reminders) */
QListWidget {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 10px;
    padding: 6px;
    color: #cdd6f4;
    outline: none;
}

QListWidget::item {
    background-color: transparent;
    color: #cdd6f4;
    border-radius: 6px;
    padding: 8px 10px;
    margin: 2px 0px;
}

QListWidget::item:hover {
    background-color: #313244;
}

QListWidget::item:selected {
    background-color: #45475a;
    color: #b4befe;
    font-weight: 600;
}

/* CheckBoxes */
QCheckBox {
    spacing: 8px;
    color: #cdd6f4;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #45475a;
    border-radius: 5px;
    background-color: #181825;
}

QCheckBox::indicator:hover {
    border-color: #b4befe;
}

QCheckBox::indicator:checked {
    background-color: #b4befe;
    border-color: #b4befe;
}

/* Sliders */
QSlider::groove:horizontal {
    height: 6px;
    background-color: #313244;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background-color: #b4befe;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background-color: #cdd6f4;
    border: 2px solid #b4befe;
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background-color: #ffffff;
    border-color: #cba6f7;
}

/* SpinBox & TimeEdit buttons */
QSpinBox::up-button, QTimeEdit::up-button, QSpinBox::down-button, QTimeEdit::down-button {
    width: 16px;
    border: none;
    background: transparent;
}

/* ScrollBar */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 2px 0 2px 0;
}

QScrollBar::handle:vertical {
    background: #45475a;
    border-radius: 4px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background: #585b70;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Context Menu */
QMenu {
    background-color: #1e1e2e;
    border: 1px solid #45475a;
    border-radius: 8px;
    padding: 6px;
    color: #cdd6f4;
}

QMenu::item {
    padding: 6px 24px 6px 12px;
    border-radius: 6px;
    margin: 1px 0px;
}

QMenu::item:selected {
    background-color: #313244;
    color: #b4befe;
}

QMenu::separator {
    height: 1px;
    background-color: #313244;
    margin: 4px 6px;
}
"""


def apply_theme(widget):
    """Apply Catppuccin dark minimalist styling to a widget or dialog."""
    widget.setStyleSheet(CATPPUCCIN_STYLE)
