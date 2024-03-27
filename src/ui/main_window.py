import shutil
import sys

from PyQt6.QtGui import QIcon
from PyQtUIkit.widgets import KitMainWindow, KitDialog

from src import config
from src.chat.panel import ChatPanel
from src.database import ChatManager
from src.gpt import translate
from src.settings_manager import SettingsManager
from src.ui.custom_themes import THEMES
from src.ui.update_manager import UpdateManager


class MainWindow(KitMainWindow):
    def __init__(self, app):
        super().__init__()
        self.setWindowTitle(config.APP_NAME)
        self.setWindowIcon(QIcon('icon.png'))

        self.sm = SettingsManager(app)
        for key, item in THEMES.items():
            self.theme_manager.add_theme(key, item)
        self.set_theme(f"{self.sm.get('dark_theme', 'light')}_{self.sm.get('theme', 'blue')}")

        self.chat_manager = ChatManager(self.sm)
        self.chat_manager.connectionErrorOccurred.connect(self._on_connection_error)
        self.chat_manager.auth()

        self._update_manager = UpdateManager(self.sm, self)
        self._update_manager.closeProgramRequested.connect(self._close)

        self._chat_widget = ChatPanel(self.sm, self.chat_manager, self._update_manager)
        self.setCentralWidget(self._chat_widget)

        translate.init(self.sm)

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

    def _on_connection_error(self):
        KitDialog.danger(self, "Ошибка", "Не удалось выполнить действие. Проверьте подключение к интернету.")

    def _close(self):
        self.close()
        sys.exit(0)
