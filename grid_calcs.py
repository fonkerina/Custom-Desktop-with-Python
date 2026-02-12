from PyQt6.QtWidgets import QApplication
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)

    screen = QApplication.primaryScreen()
    geo = screen.availableGeometry()
    print("Width:", geo.width(), "Height:", geo.height())

    sys.exit(app.exec())
