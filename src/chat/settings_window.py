import datetime
import os.path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog
from PyQtUIkit.themes.locale import KitLocaleString
from PyQtUIkit.widgets import *

from src.chat.chat_icon import ChatIcon
from src.gpt.chat import GPTChat
from src.gpt.check_providers import ModelComboBox
from src.gpt.gpt import get_models
from src.ui.update_manager import UpdateManager


class ChatSettingsWindow(KitDialog):
    def __init__(self, parent, sm, cm, um: UpdateManager, chat: GPTChat):
        super().__init__(parent)
        self._chat = chat
        self.sm = sm
        self._cm = cm
        self._um = um
        self.name = KitLocaleString.settings
        self.main_palette = 'Bg'

        self._labels = []
        self.setFixedWidth(400)

        main_layout = KitVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(8)
        self.setWidget(main_layout)

        label = KitLabel(KitLocaleString.chat_name)
        self._labels.append(label)
        main_layout.addWidget(label)

        self._name_label = KitLineEdit()
        self._name_label.editingFinished.connect(self._on_name_changed)
        self._name_label.setFixedHeight(24)
        main_layout.addWidget(self._name_label)

        layout = KitHBoxLayout()
        layout.spacing = 6
        main_layout.addWidget(layout)

        self._chat_icon = ChatIcon(self.sm, chat)
        layout.addWidget(self._chat_icon)

        self._button_import_icon = KitButton(KitLocaleString.select_file)
        self._button_import_icon.on_click = self.import_icon
        self._button_import_icon.setFixedHeight(24)
        layout.addWidget(self._button_import_icon)

        self._button_clear_icon = KitIconButton('line-close')
        self._button_clear_icon.size = 24
        self._button_clear_icon.on_click = self._chat_icon.clear_image
        layout.addWidget(self._button_clear_icon)

        self._time_label = KitLabel()
        self._labels.append(self._time_label)
        main_layout.addWidget(self._time_label)

        label = KitLabel(KitLocaleString.model)
        self._labels.append(label)
        main_layout.addWidget(label)

        self._model_box = ModelComboBox()
        main_layout.addWidget(self._model_box)

        layout = KitHBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        main_layout.addWidget(layout)

        label = KitLabel(KitLocaleString.used_messages + ':')
        self._labels.append(label)
        layout.addWidget(label)

        # self._used_messages_label = KitLabel()
        # self._used_messages_label.setFixedWidth(16)
        # layout.addWidget(self._used_messages_label)

        # self._used_messages_slider = QSlider(Qt.Orientation.Horizontal)
        # self._used_messages_slider.setRange(1, 10)
        # self._used_messages_slider.setSingleStep(50)
        # self._used_messages_slider.valueChanged.connect(lambda value: self._used_messages_label.setText(str(value)))
        # layout.addWidget(self._used_messages_slider)

        self._used_messages_box = KitSpinBox()
        self._used_messages_box.setFixedWidth(100)
        self._used_messages_box.setRange(1, 10)
        layout.addWidget(self._used_messages_box)

        layout = KitHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        main_layout.addWidget(layout)

        label = KitLabel(KitLocaleString.max_messages + ':')
        self._labels.append(label)
        layout.addWidget(label)

        self._saved_messages_box = KitSpinBox()
        self._saved_messages_box.setFixedWidth(100)
        self._saved_messages_box.setRange(50, 10000)
        layout.addWidget(self._saved_messages_box)

        layout = KitHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        main_layout.addWidget(layout)

        label = KitLabel(KitLocaleString.temperature + ':')
        self._labels.append(label)
        layout.addWidget(label)

        self._temperature_box = KitSpinBox(float)
        self._temperature_box.setFixedWidth(100)
        self._temperature_box.setMinimum(0)
        self._temperature_box.setMaximum(1)
        self._temperature_box._step = 0.01
        layout.addWidget(self._temperature_box)

        self._sync_checkbox = KitCheckBox(KitLocaleString.sync)
        self._sync_checkbox.main_palette = 'Bg'
        main_layout.addWidget(self._sync_checkbox)

        self._model_box.setCurrentIndex(get_models().index(self._chat.model))
        self._temperature_box.setValue(self._chat.temperature)
        self._saved_messages_box.setValue(self._chat.saved_messages)
        self._used_messages_box.setValue(self._chat.used_messages)
        # self._used_messages_label.setText(str(self._chat.used_messages))
        self._time_label.text = KitLocaleString.created + \
                                f": {datetime.datetime.fromtimestamp(self._chat.ctime).strftime('%D %H:%M')}"
        self._name_label.setText(self._chat.name)
        self._sync_checkbox.setChecked(self._chat.remote_id is not None)

    def save(self):
        self._chat.name = self._name_label.text
        self._chat.used_messages = self._used_messages_box.value
        self._chat.saved_messages = self._saved_messages_box.value
        self._chat.temperature = self._temperature_box.value
        self._chat.model = self._model_box.currentValue()
        self._cm.make_remote(self._chat, self._sync_checkbox.state)

    def import_icon(self):
        path, _ = QFileDialog.getOpenFileName(self, directory=self.sm.get('chat_icon_dir', '.'), filter='Image (*.png)')
        if path:
            self.sm.set('chat_icon_dir', os.path.dirname(path))
            self._chat_icon.import_image(path)

    def _on_name_changed(self):
        self._chat.name = self._name_label.text
        self._chat_icon.update_text()
