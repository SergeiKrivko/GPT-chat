import shutil

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMainWindow

from src import config
from src.chat.panel import ChatPanel
from src.chat.render_latex import rerender_all
from src.database import ChatManager
from src.settings_manager import SettingsManager
from src.ui.themes import ThemeManager
from src.ui.update_manager import UpdateManager


class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.setWindowTitle(config.APP_NAME)
        self.setWindowIcon(QIcon('icon.png'))

        self.sm = SettingsManager(app)
        self.tm = ThemeManager(self.sm, f"{self.sm.get('dark_theme', 'light')}_{self.sm.get('theme', 'grey')}")
        self.tm.themeChanged.connect(self.set_theme)

        self.chat_manager = ChatManager(self.sm)
        self.chat_manager.auth()

        self._update_manager = UpdateManager(self.sm, self.tm)
        self._update_manager.closeProgramRequested.connect(self.close)

        self._chat_widget = ChatPanel(self.sm, self.tm, self.chat_manager, self._update_manager)
        self.setCentralWidget(self._chat_widget)

        self.resize(int(self.sm.get('window_width', 300)), int(self.sm.get('window_height', 600)))
        if self.sm.get('maximized', False) not in {False, 'False', 'false', 0}:
            self.showMaximized()

    def resizeEvent(self, a0) -> None:
        super().resizeEvent(a0)
        if not self.isMaximized():
            self.sm.set('window_width', self.width())
            self.sm.set('window_height', self.height())

    def closeEvent(self, a0) -> None:
        self.sm.set('maximized', 1 if self.isMaximized() else 0)
        try:
            shutil.rmtree(f"{self.sm.app_data_dir}/temp")
        except Exception:
            pass
        super().closeEvent(a0)

    def set_theme(self):
        rerender_all(self.tm)
        self.setStyleSheet(self.tm.bg_style_sheet)
        self._chat_widget.set_theme()
