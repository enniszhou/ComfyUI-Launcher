"""ComfyUI Launcher - Main entry point."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from launcher.window import MainWindow
from launcher.settings import Settings
from launcher.theme import get_stylesheet


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ComfyUI Launcher")
    app.setApplicationVersion("1.0.0")

    # 设置应用图标
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "launcher", "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    settings = Settings()
    app.setStyleSheet(get_stylesheet(settings.theme))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
