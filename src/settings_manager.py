import appdirs
from PyQt6.QtCore import QSettings, QObject

from src import config


class SettingsManager(QObject):
    def __init__(self):
        super().__init__()
        # self.q_settings = QSettings('settings.ini', QSettings.IniFormat)
        self.q_settings = QSettings()
        self.app_data_dir = appdirs.user_data_dir(config.APP_NAME, config.ORGANISATION_NAME).replace('\\', '/')

    def get(self, key, default=None):
        return self.q_settings.value(key, default)

    def remove(self, key):
        self.q_settings.remove(key)

    def set(self, key, value):
        self.q_settings.setValue(key, value)
