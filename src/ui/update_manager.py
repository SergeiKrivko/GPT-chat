import json
import os.path
import shutil
import sys
import zipfile
from time import sleep
from urllib.parse import quote

import aiohttp
from PyQt6.QtCore import QObject, pyqtSignal
from qasync import asyncSlot

from src import config
from src.settings_manager import SettingsManager
from src.ui.custom_dialog import ask


class UpdateManager(QObject):
    closeProgramRequested = pyqtSignal()
    _askDownload = pyqtSignal(object)

    def __init__(self, sm: SettingsManager, tm):
        super().__init__()
        self._sm = sm
        self._tm = tm
        self._have_update = False
        self._new_version = None
        self.check_release(bool(self._sm.get('auto_update', True)))
        self._askDownload.connect(self._ask_download)

    @property
    def system(self):
        match sys.platform:
            case 'win32':
                return 'windows'
            case 'linux':
                return 'linux'
            case 'darwin':
                return 'macos'

    @property
    def have_update(self):
        return self._have_update

    @property
    def release_zip_path(self):
        return f"{self._sm.app_data_dir}/releases/{self.system}.zip"

    @property
    def release_exe_path(self):
        match self.system:
            case 'windows':
                filename = 'GPT-chat_setup.exe'
            case 'linux':
                filename = f'gptchat_{self._new_version}_amd64.deb'
            case 'macos':
                filename = 'GPT-chat.dmg'
            case _:
                raise ValueError
        return f"{self._sm.app_data_dir}/releases/{filename}"

    async def get_release_info(self):
        url = f"https://firebasestorage.googleapis.com/v0/b/gpt-chat-bf384.appspot.com/o/" \
              f"{quote(f'releases/{self.system}.json', safe='')}?alt=media"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                res = await resp.text()
                if not resp.ok:
                    raise aiohttp.ClientConnectionError(res)
        res = json.loads(res)
        self._new_version = res.get('version', None)
        return res

    async def download_release(self):
        url = f"https://firebasestorage.googleapis.com/v0/b/gpt-chat-bf384.appspot.com/o/" \
              f"{quote(f'releases/{self.system}.zip', safe='')}?alt=media"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if not resp.ok:
                    raise aiohttp.ClientConnectionError
                os.makedirs(os.path.dirname(self.release_zip_path), exist_ok=True)
                with open(self.release_zip_path, 'bw') as f:
                    content = await resp.content.read()
                    f.write(content)

    @asyncSlot()
    async def prepare_release(self):
        info = await self.get_release_info()
        await self.download_release()
        with zipfile.ZipFile(self.release_zip_path, 'r') as f:
            f.extractall(os.path.dirname(self.release_exe_path))
        os.remove(self.release_zip_path)
        self._sm.set('downloaded_release', info.get('version', ''))
        self._install_release()

    @staticmethod
    def compare_version(version: str):
        """
        Compare version and APP_VERSION from config
        :param version: version *.*.*
        :return: True if version > config.APP_VERSION
        """
        if version.count('.') != 2:
            return False
        for a1, a2 in zip(version.split('.'), config.APP_VERSION.split('.')):
            if a1 != a2:
                return int(a1) > int(a2)
        return False

    @asyncSlot()
    async def check_release(self, auto_update=True):
        downloaded_version = self._sm.get('downloaded_release', '')
        if not os.path.isfile(self.release_exe_path):
            downloaded_version = ''
        if self.compare_version(downloaded_version):
            self._have_update = True
            if auto_update:
                looper = self._sm.run_process(lambda: sleep(0.1), 'update_prog_timer')
                looper.finished.connect(lambda: self._install_release())
        else:
            self._sm.set('downloaded_release', '')
            if os.path.isdir(os.path.dirname(self.release_exe_path)):
                shutil.rmtree(os.path.dirname(self.release_exe_path))
            info = await self.get_release_info()
            if self.compare_version(info.get('version', '')):
                self._have_update = True
                if auto_update:
                    ver = info.get('version', '')
                    looper = self._sm.run_process(lambda: sleep(0.1), 'update_prog_timer')
                    looper.finished.connect(lambda: self._ask_download(ver))

    def _ask_download(self, version):
        if ask(self._tm, f"Доступна новая версия программы: {version}. "
                         f"Хотите загрузить обновление сейчас?") == 'Да':
            self.prepare_release()

    def _run_installer_exe(self):
        match self.system:
            case 'windows':
                os.system(f"start {self.release_exe_path}")
            case 'linux':
                os.system(f"xdg-open {self.release_exe_path}")
            case 'macos':
                os.system(f"open {self.release_exe_path}")

    def _install_release(self):
        if not os.path.isfile(self.release_exe_path):
            print("Exe not found")
            return
        if ask(self._tm, f"Версия {self._sm.get('downloaded_release')} готова к установке. Установить сейчас?") == 'Да':
            self._run_installer_exe()
            self.closeProgramRequested.emit()
