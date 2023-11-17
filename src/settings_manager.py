from types import FunctionType

import appdirs
from PyQt6.QtCore import QSettings, QObject, QThread
from PyQt6.QtWidgets import QApplication

from src import config


class SettingsManager(QObject):
    def __init__(self, app: QApplication):
        super().__init__()
        # self.q_settings = QSettings('settings.ini', QSettings.IniFormat)
        self.app = app
        self.q_settings = QSettings()
        self.app_data_dir = appdirs.user_data_dir(config.APP_NAME, config.ORGANISATION_NAME).replace('\\', '/')

        self._background_processes = dict()
        self._background_process_count = 0

    def get(self, key, default=None):
        return self.q_settings.value(key, default)

    def remove(self, key):
        self.q_settings.remove(key)

    def set(self, key, value):
        self.q_settings.setValue(key, value)

    def run_process(self, thread: QThread | FunctionType, name: str):
        if not isinstance(thread, QThread):
            thread = Looper(thread)

        if name in self._background_processes:
            self._background_processes[name].terminate()
        self._background_processes[name] = thread
        self._background_process_count += 1
        thread.finished.connect(lambda: self._on_thread_finished(name, thread))
        thread.start()
        return thread

    def _on_thread_finished(self, name, process):
        self._background_process_count -= 1
        if self._background_processes[name] == process:
            self._background_processes.pop(name)

    def all_finished(self):
        return self._background_process_count == 0

    def terminate_all(self):
        for item in self._background_processes.values():
            item.terminate()

    def copy_text(self, text):
        self.app.clipboard().setText(text)


class Looper(QThread):
    def __init__(self, func):
        super().__init__()
        self._func = func
        self.res = None

    def run(self) -> None:
        self.res = self._func()

