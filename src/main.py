"""Entry point for SolidSplash. Run with `python src/main.py`."""
import sys

from PySide6.QtWidgets import QApplication

from solidsplash.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("SolidSplash")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
