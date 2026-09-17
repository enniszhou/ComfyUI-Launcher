"""Theme management for dark/light mode."""

DARK_STYLESHEET = """
QMainWindow {
    background-color: #1e1e2e;
    color: #cdd6f4;
}
QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-size: 13px;
}
QGroupBox {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 8px;
    color: #89b4fa;
}
QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #45475a;
}
QPushButton:pressed {
    background-color: #585b70;
}
QPushButton:disabled {
    background-color: #313244;
    color: #6c7086;
}
QPushButton#primaryBtn {
    background-color: #89b4fa;
    color: #1e1e2e;
    font-weight: bold;
    border: none;
}
QPushButton#primaryBtn:hover {
    background-color: #74c7ec;
}
QPushButton#dangerBtn {
    background-color: #f38ba8;
    color: #1e1e2e;
    font-weight: bold;
    border: none;
}
QPushButton#dangerBtn:hover {
    background-color: #eba0ac;
}
QPushButton#successBtn {
    background-color: #a6e3a1;
    color: #1e1e2e;
    font-weight: bold;
    border: none;
}
QPushButton#successBtn:hover {
    background-color: #94e2d5;
}
QLineEdit, QSpinBox, QComboBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border-color: #89b4fa;
}
QTextEdit {
    background-color: #181825;
    color: #a6adc8;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 8px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
}
QTabWidget::pane {
    border: 1px solid #313244;
    border-radius: 6px;
    background-color: #1e1e2e;
}
QTabBar::tab {
    background-color: #181825;
    color: #a6adc8;
    padding: 8px 20px;
    border: 1px solid #313244;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected {
    background-color: #1e1e2e;
    color: #89b4fa;
    border-bottom: 2px solid #89b4fa;
}
QCheckBox {
    color: #cdd6f4;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #45475a;
    background-color: #313244;
}
QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}
QLabel {
    color: #cdd6f4;
}
QLabel#statusLabel {
    font-size: 16px;
    font-weight: bold;
    color: #89b4fa;
}
QLabel#infoLabel {
    color: #a6adc8;
    font-size: 12px;
}
QScrollBar:vertical {
    background-color: #181825;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background-color: #45475a;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #585b70;
}
QListWidget {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    outline: none;
}
QListWidget::item {
    padding: 8px;
    border-bottom: 1px solid #313244;
}
QListWidget::item:selected {
    background-color: #313244;
}
QListWidget::item:hover {
    background-color: #252537;
}
QProgressBar {
    background-color: #313244;
    border-radius: 5px;
    text-align: center;
    color: #cdd6f4;
    border: none;
    height: 20px;
}
QProgressBar::chunk {
    background-color: #89b4fa;
    border-radius: 5px;
}
"""

LIGHT_STYLESHEET = """
QMainWindow {
    background-color: #ffffff;
    color: #1e1e2e;
}
QWidget {
    background-color: #ffffff;
    color: #1e1e2e;
    font-size: 13px;
}
QGroupBox {
    background-color: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 8px;
    color: #0d6efd;
}
QPushButton {
    background-color: #e9ecef;
    color: #1e1e2e;
    border: 1px solid #ced4da;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #dee2e6;
}
QPushButton#primaryBtn {
    background-color: #0d6efd;
    color: #ffffff;
    font-weight: bold;
    border: none;
}
QPushButton#dangerBtn {
    background-color: #dc3545;
    color: #ffffff;
    font-weight: bold;
    border: none;
}
QPushButton#successBtn {
    background-color: #198754;
    color: #ffffff;
    font-weight: bold;
    border: none;
}
QLineEdit, QSpinBox, QComboBox {
    background-color: #ffffff;
    color: #1e1e2e;
    border: 1px solid #ced4da;
    border-radius: 6px;
    padding: 6px 10px;
}
QTextEdit {
    background-color: #f8f9fa;
    color: #495057;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    padding: 8px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
}
QTabBar::tab {
    background-color: #f8f9fa;
    color: #495057;
    padding: 8px 20px;
    border: 1px solid #dee2e6;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected {
    background-color: #ffffff;
    color: #0d6efd;
    border-bottom: 2px solid #0d6efd;
}
QListWidget {
    background-color: #f8f9fa;
    color: #1e1e2e;
    border: 1px solid #dee2e6;
    border-radius: 6px;
}
QListWidget::item:selected {
    background-color: #e9ecef;
}
QProgressBar {
    background-color: #e9ecef;
    border-radius: 5px;
    text-align: center;
    border: none;
    height: 20px;
}
QProgressBar::chunk {
    background-color: #0d6efd;
    border-radius: 5px;
}
"""


def get_stylesheet(theme: str = "dark") -> str:
    if theme == "light":
        return LIGHT_STYLESHEET
    return DARK_STYLESHEET
