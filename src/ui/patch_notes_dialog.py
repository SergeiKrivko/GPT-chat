import asyncio
import json
from time import sleep

import aiohttp
from PyQt6.QtCore import Qt, pyqtSignal
from PyQtUIkit.core import KitFont
from PyQtUIkit.themes.local import KitLocalString
from PyQtUIkit.widgets import *
from qasync import asyncSlot

from src import config
from src.settings_manager import SettingsManager


class Version:
    def __init__(self, version: str):
        major, minor, patch = version.split('.')
        self.major = int(major)
        self.minor = int(minor)
        self.patch = int(patch)

    def __cmp__(self, other: 'Version'):
        if self.major != other.major:
            return self.major - other.major
        if self.minor != other.minor:
            return self.minor - other.minor
        return self.patch - other.patch

    def __eq__(self, other):
        return self.__cmp__(other) == 0

    def __gt__(self, other):
        return self.__cmp__(other) > 0

    def __lt__(self, other):
        return self.__cmp__(other) < 0

    def __ge__(self, other):
        return self.__cmp__(other) >= 0

    def __le__(self, other):
        return self.__cmp__(other) <= 0

    def __str__(self):
        return f"{self.major}.{self.minor}.{self.patch}"


class PatchNotesDialog(KitDialog):
    execRequired = pyqtSignal()

    def __init__(self, parent, sm: SettingsManager):
        super().__init__(parent)
        self.name = KitLocalString.patch_note
        self._sm = sm
        self.setFixedSize(600, 400)

        self._session = aiohttp.ClientSession("https://raw.githubusercontent.com")
        self._current_index = 0
        self._versions: list[Version] = []

        main_layout = KitHBoxLayout()
        main_layout.padding = 5
        main_layout.spacing = 5
        self.setWidget(main_layout)

        left_layout = KitVBoxLayout()
        left_layout.setFixedWidth(24)
        left_layout.alignment = Qt.AlignmentFlag.AlignCenter
        main_layout.addWidget(left_layout)

        self._button_prev = KitIconButton('line-chevron-back')
        self._button_prev.setFixedSize(24, 40)
        self._button_prev.on_click = self._prev
        left_layout.addWidget(self._button_prev)

        self._tab_layout = KitTabLayout()
        main_layout.addWidget(self._tab_layout, 100)

        spinner = KitSpinner()
        self._tab_layout.addWidget(spinner)

        layout = KitVBoxLayout()
        layout.spacing = 6
        self._tab_layout.addWidget(layout)

        self._version_label = KitLabel()
        self._version_label.setContentsMargins(5, 0, 0, 0)
        self._version_label.font_size = KitFont.Size.SUPER_BIG
        self._version_label.font = 'bold'
        layout.addWidget(self._version_label)

        layout.addWidget(KitHSeparator())

        self._text_edit = KitTextEdit()
        self._text_edit.border = 0
        self._text_edit.setReadOnly(True)
        self._text_edit.main_palette = 'Bg'
        layout.addWidget(self._text_edit)

        right_layout = KitVBoxLayout()
        right_layout.setFixedWidth(24)
        right_layout.alignment = Qt.AlignmentFlag.AlignCenter
        main_layout.addWidget(right_layout)

        self._button_next = KitIconButton('line-chevron-forward')
        self._button_next.setFixedSize(24, 40)
        self._button_next.on_click = self._next
        right_layout.addWidget(self._button_next)

        self.execRequired.connect(self._exec)
        self._run()

    @asyncSlot()
    async def _run(self):
        await self._download_versions()
        version = Version(self._sm.get('last_view_patch_note_version', '0.0.0'))

        while self._current_index < len(self._versions) and self._versions[self._current_index] <= version:
            self._current_index += 1

        if self._current_index < len(self._versions):
            await self._open_note(self._versions[self._current_index])
            if self._versions[self._current_index] <= Version(config.APP_VERSION):
                self.execRequired.emit()
        else:
            self._current_index -= 1
            await self._open_note(self._versions[self._current_index])
        self._update_buttons()

    def _exec(self):
        self._sm.run_process(lambda: sleep(0.1), 'patch-notes-sleep').finished.connect(lambda: self.exec())

    async def _download_versions(self):
        while True:
            try:
                async with self._session.get("/SergeiKrivko/GPT-chat/master/patch_notes/versions.json") as resp:
                    if resp.ok:
                        res = await resp.text()
                        for version in json.loads(res):
                            self._versions.append(Version(version.replace('-', '.')))
                        break
            except aiohttp.ClientConnectionError:
                pass
            await asyncio.sleep(20)

    async def _download_note(self, version: Version):
        while True:
            try:
                async with self._session.get(f"/SergeiKrivko/GPT-chat/master/patch_notes/"
                                             f"{str(version).replace('.', '-')}.md") as resp:
                    if resp.ok:
                        res = await resp.text()
                        return res
            except aiohttp.ClientConnectionError:
                pass
            await asyncio.sleep(5)
            while self.isHidden():
                await asyncio.sleep(5)

    async def _open_note(self, version: Version):
        self._tab_layout.setCurrent(0)
        text = await self._download_note(version)
        self._tab_layout.setCurrent(1)
        cur_version = Version(config.APP_VERSION)

        if version == cur_version:
            version_desc = KitLocalString.current_version
        elif version > cur_version:
            version_desc = KitLocalString.next_version
        else:
            version_desc = KitLocalString.last_version

        self._version_label.text = KitLocalString.version + ' ' + str(version) + ' (' + version_desc + ')'
        self._text_edit.setMarkdown(text)
        html = self._text_edit.toHtml().replace("font-family:'Courier New'", "font-family:'Roboto Mono'").replace(
            "font-family:'Segoe UI'", "font-family:'Roboto'").replace('font-size:9pt', 'font-size:11pt')
        self._text_edit.setHtml(html)
        self._store_version()

    def _store_version(self):
        if self.isHidden():
            return
        version = self._versions[self._current_index]
        if version > Version(self._sm.get('last_view_patch_note_version', '0.0.0')):
            self._sm.set('last_view_patch_note_version', str(version))

    def showEvent(self, a0) -> None:
        super().showEvent(a0)
        self._store_version()

    @asyncSlot()
    async def open_note(self, version: Version):
        await self._open_note(version)
        self._update_buttons()

    def _next(self):
        if self._current_index < len(self._versions) - 1:
            self._current_index += 1
            self.open_note(self._versions[self._current_index])

    def _prev(self):
        if self._current_index > 0:
            self._current_index -= 1
            self.open_note(self._versions[self._current_index])

    def _update_buttons(self):
        self._button_next.setHidden(self._current_index >= len(self._versions) - 1)
        self._button_prev.setHidden(self._current_index <= 0)
