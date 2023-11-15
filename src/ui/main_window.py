from PyQt6.QtWidgets import QMainWindow

from src import config
from src.chat import ChatPanel
from src.settings_manager import SettingsManager
from src.ui.themes import ThemeManager


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(config.APP_NAME)

        self.sm = SettingsManager()
        self.tm = ThemeManager(self.sm, self.sm.get('theme', 'basic'))

        self._chat_widget = ChatPanel(self.sm, self.tm)
        self.setCentralWidget(self._chat_widget)

        self.resize(self.sm.get('window_width', 300), self.sm.get('window_height', 600))

    def resizeEvent(self, a0) -> None:
        super().resizeEvent(a0)
        self.sm.set('window_width', self.width())
        self.sm.set('window_height', self.height())

    def set_theme(self):
        self.setStyleSheet(self.tm.bg_style_sheet)
        self._chat_widget.set_theme()
