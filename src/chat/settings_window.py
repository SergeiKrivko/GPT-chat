import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQtUIkit.widgets import *

from src.gpt.chat import GPTChat
from src.gpt.gpt import get_models
from src.ui.update_manager import UpdateManager


class ChatSettingsWindow(KitDialog):
    def __init__(self, parent, sm, cm, um: UpdateManager, chat: GPTChat):
        super().__init__(parent)
        self._chat = chat
        self.sm = sm
        self._cm = cm
        self._um = um
        self.name = "Настройки"
        self.main_palette = 'Bg'

        self._labels = []
        self.setFixedWidth(400)

        main_layout = KitVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(8)
        self.setWidget(main_layout)

        self._theme_checkbox = KitCheckBox("Темная тема")
        self._theme_checkbox.main_palette = 'Bg'
        self._theme_checkbox.setState(self.sm.get('dark_theme', 'light') == 'dark')
        self._theme_checkbox.stateChanged.connect(self._on_theme_changed)
        main_layout.addWidget(self._theme_checkbox)

        layout = KitHBoxLayout()
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        main_layout.addWidget(layout)

        label = KitLabel("Оформление:")
        self._labels.append(label)
        layout.addWidget(label)

        self._theme_box = KitComboBox('blue', 'green', 'red', 'orange', 'pink')
        self._theme_box.setCurrentIndex(['blue', 'green', 'red', 'orange', 'pink'].index(self.sm.get('theme', 'blue')))
        self._theme_box.currentValueChanged.connect(self._on_theme_changed)
        layout.addWidget(self._theme_box)

        self._update_widget = UpdateWidget()
        self._um.set_widget(self._update_widget)
        self._update_widget.clicked.connect(lambda: self._um.check_release(say_if_no_release=True))
        self._update_widget.cancel.connect(lambda: self._um.cancel_downloading())
        main_layout.addWidget(self._update_widget)

        self._auto_update_checkbox = KitCheckBox("Сообщать об обновлениях")
        self._auto_update_checkbox.main_palette = 'Bg'
        self._auto_update_checkbox.setState(bool(self.sm.get('auto_update', True)))
        main_layout.addWidget(self._auto_update_checkbox)

        self._separator = KitHBoxLayout()
        self._separator.main_palette = 'Border'
        self._separator.setFixedHeight(1)
        main_layout.addWidget(self._separator)

        label = KitLabel("Название диалога")
        self._labels.append(label)
        main_layout.addWidget(label)

        self._name_label = KitLineEdit()
        self._name_label.setFixedHeight(24)
        main_layout.addWidget(self._name_label)

        self._time_label = KitLabel()
        self._labels.append(self._time_label)
        main_layout.addWidget(self._time_label)

        label = KitLabel("Модель")
        self._labels.append(label)
        main_layout.addWidget(label)

        self._model_box = KitComboBox()
        for el in get_models():
            self._model_box.addItem(el)
        main_layout.addWidget(self._model_box)

        layout = KitHBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        main_layout.addWidget(layout)

        label = KitLabel("Используемые сообщения:")
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

        label = KitLabel("Максимум сообщений:")
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

        label = KitLabel("Temperature:")
        self._labels.append(label)
        layout.addWidget(label)

        self._temperature_box = KitSpinBox(float)
        self._temperature_box.setFixedWidth(100)
        self._temperature_box.setMinimum(0)
        self._temperature_box.setMaximum(1)
        self._temperature_box._step = 0.01
        layout.addWidget(self._temperature_box)

        self._sync_checkbox = KitCheckBox("Синхронизировать")
        self._sync_checkbox.main_palette = 'Bg'
        main_layout.addWidget(self._sync_checkbox)

        if self._chat is not None:
            self._model_box.setCurrentIndex(get_models().index(self._chat.model))
            self._temperature_box.setValue(self._chat.temperature)
            self._saved_messages_box.setValue(self._chat.saved_messages)
            self._used_messages_box.setValue(self._chat.used_messages)
            # self._used_messages_label.setText(str(self._chat.used_messages))
            self._time_label.setText(
                f"Создан: {datetime.datetime.fromtimestamp(self._chat.ctime).strftime('%D %H:%M')}")
            self._name_label.setText(self._chat.name)
            self._sync_checkbox.setState(self._chat.remote_id is not None)
        else:
            self._temperature_box.hide()
            self._saved_messages_box.hide()
            self._used_messages_box.hide()
            self._model_box.hide()
            self._time_label.hide()
            self._name_label.hide()
            self._sync_checkbox.hide()
            for el in self._labels[1:]:
                el.hide()

    def save(self):
        self.sm.set('auto_update', 'true' if self._auto_update_checkbox.state() else '')
        if self._chat is not None:
            self._chat.name = self._name_label.text()
            self._chat.used_messages = self._used_messages_box.value()
            self._chat.saved_messages = self._saved_messages_box.value()
            self._chat.temperature = self._temperature_box.value()
            self._chat.model = self._model_box.currentValue()
            self._cm.make_remote(self._chat, self._sync_checkbox.state())

    def _on_theme_changed(self):
        self.sm.set('dark_theme', 'dark' if self._theme_checkbox.state() else 'light')
        self.sm.set('theme', self._theme_box.currentValue())
        self.theme_manager.set_theme(f"{self.sm.get('dark_theme')}_{self.sm.get('theme')}")
        self._apply_theme()


class UpdateWidget(KitTabLayout):
    NO_RELEASE = 0
    READY_TO_DOWNLOAD = 1
    DOWNLOADING = 2
    READY_TO_INSTALL = 3

    clicked = pyqtSignal()
    cancel = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setContentsMargins(0, 0, 0, 0)

        self._button_check = KitButton("Проверить обновление")
        self._button_check.clicked.connect(self.clicked.emit)
        self.addWidget(self._button_check)

        self._button_download = KitButton("Скачать обновление")
        self._button_download.clicked.connect(self.clicked.emit)
        self.addWidget(self._button_download)

        progress_layout = KitHBoxLayout()
        progress_layout.setContentsMargins(0, 0, 0, 0)
        self.addWidget(progress_layout)

        self._progress_bar = KitProgressBar()
        self._progress_bar.setFixedHeight(24)
        progress_layout.addWidget(self._progress_bar)

        self._button_cancel = KitIconButton('solid-xmark')
        self._button_cancel.size = 24
        self._button_cancel.clicked.connect(self.cancel.emit)
        progress_layout.addWidget(self._button_cancel)

        self._button_install = KitButton("Установить обновление")
        self._button_install.clicked.connect(self.clicked.emit)
        self.addWidget(self._button_install)

    def set_status(self, status):
        self.setCurrent(status)

    def set_progress(self, value):
        self.set_status(UpdateWidget.DOWNLOADING)
        self._progress_bar.setValue(value)
