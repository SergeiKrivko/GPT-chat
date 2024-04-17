import os
import shutil
import sys

from PyQt6.QtGui import QIcon
from PyQtUIkit.themes.local import KitLocalString
from PyQtUIkit.widgets import KitMainWindow, KitDialog

from src import config
from src.chat.panel import ChatPanel
from src.database import ChatManager
from src.gpt import translate, gpt
from src.settings_manager import SettingsManager
from src.ui.custom_themes import THEMES
from src.ui.update_manager import UpdateManager


class MainWindow(KitMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(config.APP_NAME)
        self.setWindowIcon(QIcon('icon.png'))

        for el in os.listdir(config.ASSETS_DIR):
            self.theme_manager.add_icon(f"{config.ASSETS_DIR}/{el}", 'custom-' + el[:-4])

        self.sm = SettingsManager()
        for key, item in THEMES.items():
            self.theme_manager.add_theme(key, item)
        self.set_theme(f"{self.sm.get('dark_theme', 'light')}_{self.sm.get('theme', 'blue')}")
        
        self.theme_manager.set_lang_path('src.ui.local')
        self.theme_manager.set_lang(self.sm.get('language'))

        self.chat_manager = ChatManager(self.sm)
        self.chat_manager.connectionErrorOccurred.connect(self._on_connection_error)
        self.chat_manager.auth()

        self._update_manager = UpdateManager(self.sm, self)
        self._update_manager.closeProgramRequested.connect(self._close)

        self._chat_widget = ChatPanel(self.sm, self.chat_manager, self._update_manager)
        self.setCentralWidget(self._chat_widget)

        translate.init(self.sm)

        self.__previous_size = (0, 0)
        self.__size = (0, 0)
        self.resize(int(self.sm.get('window_width', 300)), int(self.sm.get('window_height', 600)))
        if self.sm.get('maximized', False) not in {False, 'False', 'false', 0}:
            self.showMaximized()

        self.sm.run_process(gpt.init, 'g4f-import')

    def resizeEvent(self, a0) -> None:
        super().resizeEvent(a0)
        self.__previous_size = self.__size
        self.__size = (self.width(), self.height())
        self.sm.set('window_width', self.width())
        self.sm.set('window_height', self.height())

    def closeEvent(self, a0) -> None:
        self.sm.set('maximized', 1 if self.isMaximized() else 0)
        if self.isMaximized():
            self.sm.set('window_width', self.__previous_size[0])
            self.sm.set('window_height', self.__previous_size[1])
        try:
            shutil.rmtree(f"{self.sm.app_data_dir}/temp")
        except Exception:
            pass
        super().closeEvent(a0)

    def _on_connection_error(self):
        KitDialog.danger(self, KitLocalString.error, KitLocalString.connection_error)

    def _close(self):
        self.close()
        sys.exit(0)
