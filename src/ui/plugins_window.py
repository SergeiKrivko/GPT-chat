import json
import os
import shutil

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import QFileDialog
from PyQtUIkit.themes.locale import KitLocaleString
from PyQtUIkit.widgets import *

from src.database import ChatManager
from src.gpt.gpt import plugins
from src.gpt.plugins import Plugin
from src.settings_manager import SettingsManager


class PluginsWindow(KitDialog):
    def __init__(self, parent, sm: SettingsManager, cm: ChatManager):
        super().__init__(parent)
        self._sm = sm
        self._cm = cm
        self.name = KitLocaleString.custom_providers
        self.setFixedSize(400, 320)

        main_layout = KitVBoxLayout()
        self.setWidget(main_layout)

        self._scroll_area = KitScrollArea()
        self._scroll_area.main_palette = 'Bg'
        main_layout.addWidget(self._scroll_area)

        layout = KitVBoxLayout()
        layout.alignment = Qt.AlignmentFlag.AlignTop
        layout.padding = 10
        layout.spacing = 6
        self._scroll_area.setWidget(layout)

        self._scroll_layout = KitVBoxLayout()
        self._scroll_layout.spacing = 6
        self._scroll_layout.alignment = Qt.AlignmentFlag.AlignTop
        layout.addWidget(self._scroll_layout)

        self._button_add = KitButton(KitLocaleString.add)
        self._button_add.on_click = self._import_plugin
        layout.addWidget(self._button_add)

    def showEvent(self, a0) -> None:
        super().showEvent(a0)
        self._load()

    def _import_plugin(self):
        path = QFileDialog.getExistingDirectory()
        if path:
            os.makedirs(os.path.join(self._sm.app_data_dir, 'plugins'), exist_ok=True)

            try:
                with open(os.path.join(path, 'gptchat-provider-config.json'), encoding='utf-8') as f:
                    data = json.load(f)
                    name = str(data['name'])
            except FileNotFoundError:
                KitDialog.danger(self, KitLocaleString.error, KitLocaleString.invalid_provider.get(self.theme_manager))
            except KeyError:
                KitDialog.danger(self, KitLocaleString.error, KitLocaleString.invalid_provider.get(self.theme_manager))
            else:
                dst_path = os.path.join(self._sm.app_data_dir, 'plugins', name)
                shutil.copytree(path, dst_path)

                plugin = Plugin(dst_path)
                plugins[plugin.name] = plugin
                self._sm.set('plugins', json.dumps(list(plugins.keys())))

                item = PluginItem(plugin)
                item.deleteRequested.connect(self._on_delete_requested)
                self._scroll_layout.addWidget(item)

    def _load(self):
        self._scroll_layout.clear()
        for el in json.loads(self._sm.get('plugins', '[]')):
            item = PluginItem(plugins[el])
            item.deleteRequested.connect(self._on_delete_requested)
            self._scroll_layout.addWidget(item)

    def _on_delete_requested(self, item: 'PluginItem'):
        self._scroll_layout.removeWidget(item)
        plugins.pop(item.plugin.name)

        self._cm.clear_model(f'__plugin_{item.plugin.name}')
        shutil.rmtree(os.path.join(self._sm.app_data_dir, 'plugins', item.plugin.name))

        self._sm.set('plugins', json.dumps(list(plugins.keys())))


class PluginItem(KitHBoxLayout):
    deleteRequested = pyqtSignal(object)

    def __init__(self, plugin: Plugin):
        super().__init__()
        self.plugin = plugin
        self.padding = 4
        self.setFixedHeight(32)
        self.main_palette = 'Main'

        self._label = KitLabel(f"{plugin.name} {plugin.version}")
        self.addWidget(self._label)

        self._button_delete = KitIconButton('line-trash')
        self._button_delete.size = 24
        self._button_delete.border = 0
        self._button_delete.on_click = lambda: self.deleteRequested.emit(self)
        self.addWidget(self._button_delete)
