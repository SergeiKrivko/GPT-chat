import sys

from PyQt6.QtWidgets import QApplication

from src import config
from src.ui.main_window import MainWindow


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName(config.ORGANISATION_NAME)
    app.setOrganizationDomain(config.ORGANISATION_URL)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(config.APP_VERSION)

    window = MainWindow(app)

    window.show()
    window.set_theme()
    sys.excepthook = except_hook
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
