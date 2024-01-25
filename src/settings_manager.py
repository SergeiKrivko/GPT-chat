import asyncio
from types import FunctionType, LambdaType

import aiohttp
import appdirs
from PyQt6.QtCore import QSettings, QObject, QThread
from PyQt6.QtWidgets import QApplication
from qasync import asyncSlot

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

        self._authorized = False
        self._authorization()

    @property
    def authorized(self):
        return self._authorized

    @authorized.setter
    def authorized(self, value):
        self._authorized = value

    @asyncSlot()
    async def _authorization(self):
        while not self._authorized:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                            f"https://securetoken.googleapis.com/v1/token?key={config.FIREBASE_API_KEY}",
                            data={
                                'grant_type': 'refresh_token',
                                'refresh_token': self.get('user_refresh_token')
                            }) as resp:
                        if resp.ok:
                            res = await resp.json()
                            self._authorized = True
                            self.set('user_token', res['access_token'])
                            self.set('user_refresh_token', res['refresh_token'])
                            await asyncio.sleep(float(res['expires_in']) - 10)
                        else:
                            self.set('user_token', '')

            except aiohttp.ClientConnectionError:
                pass
            await asyncio.sleep(5)

    @property
    def user_data_path(self):
        if not (uid := self.get('user_id')):
            return f"{self.app_data_dir}/default_user"
        return f"{self.app_data_dir}/users-2/{uid}"

    def get(self, key, default=None):
        return self.q_settings.value(key, default)

    def remove(self, key):
        self.q_settings.remove(key)

    def set(self, key, value):
        self.q_settings.setValue(key, value)

    def run_process(self, thread: QThread | FunctionType | LambdaType, name: str):
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
