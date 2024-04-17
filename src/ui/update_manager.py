import json
import os.path
import shutil
import sys
import zipfile
from time import sleep
from urllib.parse import quote

import aiohttp
from PyQt6.QtCore import QObject, pyqtSignal
from PyQtUIkit.themes.local import KitLocalString
from PyQtUIkit.widgets import KitDialog
from qasync import asyncSlot

from src import config
from src.settings_manager import SettingsManager


class UpdateManager(QObject):
    closeProgramRequested = pyqtSignal()
    _askDownload = pyqtSignal(object)

    def __init__(self, sm: SettingsManager, parent):
        super().__init__()
        self._sm = sm
        self._parent = parent
        self._tm = parent.theme_manager
        self._have_update = False
        self._new_version = self._sm.get('downloaded_release')
        self.check_release(bool(self._sm.get('auto_update', True)))
        self._askDownload.connect(self._ask_download)
        self.widget = None
        self.__cancel = False

    def set_widget(self, w):
        self.widget = w
        if self.widget:
            self.widget.set_status(0 if not self.have_update else 1 if not os.path.isfile(self.release_exe_path) else 3)

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

    async def download_release(self, info):
        self.__cancel = False
        if self.widget:
            self.widget.set_status(2)
        url = f"https://firebasestorage.googleapis.com/v0/b/gpt-chat-bf384.appspot.com/o/" \
              f"{quote(f'releases/{self.system}.zip', safe='')}?alt=media"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if not resp.ok:
                    raise aiohttp.ClientConnectionError
                os.makedirs(os.path.dirname(self.release_zip_path), exist_ok=True)
                with open(self.release_zip_path, 'bw') as f:
                    while True:
                        chunk = await resp.content.readany()
                        if self.__cancel or not chunk:
                            break
                        f.write(chunk)
                        if self.widget:
                            self.widget.set_progress(os.path.getsize(self.release_zip_path) * 100 // info.get('size'))

    def cancel_downloading(self):
        self.__cancel = True
        self.widget.set_status(1)

    @asyncSlot()
    async def prepare_release(self):
        info = await self.get_release_info()
        await self.download_release(info)
        if self.__cancel:
            if self.widget:
                self.widget.set_status(1)
                os.remove(self.release_zip_path)
            return
        with zipfile.ZipFile(self.release_zip_path, 'r') as f:
            f.extractall(os.path.dirname(self.release_exe_path))
        os.remove(self.release_zip_path)
        self._sm.set('downloaded_release', info.get('version', ''))
        if self.widget:
            self.widget.set_status(3)
        self._install_release()

    @staticmethod
    def compare_version(version: str, cur_version=None):
        """
        Compare version and APP_VERSION from config
        :param version: version `*.*.*`
        :param cur_version: current version `*.*.*` (config.APP_VERSION if None)
        :return: True if version > current_version
        """
        cur_version = cur_version or config.APP_VERSION
        if version.count('.') != 2:
            return False
        for a1, a2 in zip(version.split('.'), cur_version.split('.')):
            if a1 != a2:
                return int(a1) > int(a2)
        return False

    @asyncSlot()
    async def check_release(self, auto_update=True, say_if_no_release=False):
        try:
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
                elif say_if_no_release:
                    looper = self._sm.run_process(lambda: sleep(0.1), 'update_prog_timer')
                    looper.finished.connect(self._on_no_release)
        except aiohttp.ClientConnectionError:
            if say_if_no_release:
                looper = self._sm.run_process(lambda: sleep(0.1), 'update_prog_timer')
                looper.finished.connect(self._on_connection_error)

    def _on_no_release(self):
        KitDialog.success(self._parent, KitLocalString.update.get(self._tm),
                          KitLocalString.last_version_installed.get(self._tm) + f": {config.APP_VERSION}")

    def _on_connection_error(self):
        KitDialog.warning(self._parent, KitLocalString.update.get(self._tm),
                          KitLocalString.check_update_connection_error.get(self._tm))

    def _ask_download(self, version):
        if KitDialog.question(self._parent, f"{KitLocalString.new_version_available.get(self._tm)}: "
                                            f"{version}. {KitLocalString.want_to_download_update.get(self._tm)}",
                              (KitLocalString.no.get(self._tm), KitLocalString.yes.get(self._tm))) == KitLocalString.yes.get(self._tm):
            self.prepare_release()

    def _run_installer_exe(self):
        match self.system:
            case 'windows':
                os.system(f"start {self.release_exe_path}")
            case 'linux':
                # os.system(f"xdg-open {self.release_exe_path}")
                with open(script := f"{os.path.dirname(self.release_exe_path)}/script", 'w', encoding='utf-8') as f:
                    f.write(f"echo \"{KitLocalString.sudo_required.get(self._tm)}\"\n"
                            f"sudo dpkg -r gptchat\nsudo dpkg -i {self.release_exe_path}\n"
                            f"/opt/{config.ORGANISATION_NAME}/{config.APP_NAME}/{config.APP_NAME}\n")
                os.system(f'chmod 755 {script}')
                os.system(f"gnome-terminal -- {script}")
            case 'macos':
                os.system(f"open {self.release_exe_path}")

    def _install_release(self):
        if not os.path.isfile(self.release_exe_path):
            print("Exe not found")
            return
        if self.widget:
            self.widget.set_status(3)
        if KitDialog.question(self._parent, f"{KitLocalString.ready_to_install.get(self._tm).format(self._sm.get('downloaded_release'))}. "
                                            f"{KitLocalString.install_now.get(self._tm)}",
                              (KitLocalString.no.get(self._tm), KitLocalString.yes.get(self._tm))) == KitLocalString.yes.get(self._tm):
            self._run_installer_exe()
            self.closeProgramRequested.emit()
