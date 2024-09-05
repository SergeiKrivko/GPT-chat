import asyncio
import os
import sys
from datetime import datetime
from typing import Callable, Any

import aiohttp
import appdirs
from PyQt6.QtCore import QSettings, QObject, QThread
from PyQtUIkit.widgets import KitAsyncApplication
from qasync import asyncSlot

from src import config


class SettingsManager(QObject):
    def __init__(self):
        super().__init__()
        # self.q_settings = QSettings('settings.ini', QSettings.IniFormat)
        self.q_settings = QSettings(config.ORGANISATION_NAME, config.APP_NAME)
        self.app_data_dir = appdirs.user_data_dir(config.APP_NAME, config.ORGANISATION_NAME).replace('\\', '/')

        self._background_processes = dict()
        self._background_process_count = 0

        os.makedirs(f'{self.app_data_dir}/logs', exist_ok=True)
        date = datetime.now().isoformat().replace(':', '_')
        self.logs_out_file = open(f'{self.app_data_dir}/logs/{date}-stdout.txt', 'w')
        self.logs_err_file = open(f'{self.app_data_dir}/logs/{date}-stderr.txt', 'w')
        sys.stdout = self.logs_out_file
        sys.stderr = self.logs_err_file

    def __del__(self):
        self.logs_out_file.close()
        self.logs_err_file.close()

    @property
    def user_data_path(self):
        if not (uid := self.get('user_id')):
            return f"{self.app_data_dir}/default_user"
        return f"{self.app_data_dir}/users/{uid}"

    def get(self, key, default=None):
        return self.q_settings.value(key, default)

    def remove(self, key):
        self.q_settings.remove(key)

    def set(self, key, value):
        self.q_settings.setValue(key, value)

    def run_process(self, thread: QThread | Callable[[], Any], name: str) -> QThread:
        if not isinstance(thread, QThread):
            thread = Looper(thread)

        if name in self._background_processes:
            self._background_processes[name].terminate()
        self._background_processes[name] = thread
        self._background_process_count += 1
        thread.finished.connect(lambda: self._on_thread_finished(name, thread))
        thread.start()
        return thread

    async def run_async(self, thread: QThread | Callable[[], Any], name: str):
        thread = self.run_process(thread, name)
        while thread.isRunning():
            await asyncio.sleep(0.2)
        if isinstance(thread, Looper):
            return thread.res
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
        KitAsyncApplication.clipboard().setText(text)


class Looper(QThread):
    def __init__(self, func):
        super().__init__()
        self._func = func
        self.res = None

    def run(self) -> None:
        self.res = self._func()
