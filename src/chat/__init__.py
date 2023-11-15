import os
import shutil
from time import time, sleep
from uuid import UUID

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QWidget, QVBoxLayout, QLabel

from src.chat import gpt
from src.chat.gpt_dialog import GPTDialog
from src.chat.chat_widget import ChatWidget
from src.chat.chats_list import GPTListWidget
from src.chat.settings_window import ChatSettingsWindow
from src.ui.button import Button
from src.ui.custom_dialog import CustomDialog


class ChatPanel(QWidget):
    def __init__(self, sm, tm):
        super().__init__()
        self.sm = sm
        self.tm = tm
        self._data_path = f"{self.sm.app_data_dir}/dialogs"
        try:
            shutil.rmtree(f"{sm.app_data_dir}/temp")
        except Exception:
            pass

        self._layout = QHBoxLayout()
        self._layout.setContentsMargins(10, 10, 0, 10)
        self.setLayout(self._layout)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        self._layout.addLayout(main_layout, 0)

        top_layout = QHBoxLayout()
        top_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        main_layout.addLayout(top_layout)

        self._button_add = Button(self.tm, 'plus', css='Bg')
        self._button_add.setFixedSize(36, 36)
        self._button_add.clicked.connect(self._new_dialog)
        top_layout.addWidget(self._button_add)

        self._button_add_special = Button(self.tm, 'plus', css='Bg')
        self._button_add_special.setFixedSize(36, 36)
        self._button_add_special.clicked.connect(self._new_special_dialog)
        top_layout.addWidget(self._button_add_special)

        self._button_settings = Button(self.tm, 'generate', css='Bg')
        self._button_settings.setFixedSize(36, 36)
        self._button_settings.clicked.connect(self._open_settings)
        top_layout.addWidget(self._button_settings)

        self._list_widget = GPTListWidget(tm)
        main_layout.addWidget(self._list_widget)
        self._list_widget.deleteItem.connect(self._delete_dialog)
        self._list_widget.currentItemChanged.connect(self._select_dialog)

        self.dialogs = dict()
        self.chat_widgets = dict()
        self.current = None

        # self._last_dialog = UUID(self.sm.get('current_dialog', ''))
        # self._loader = DialogLoader(self._data_path)
        # self._loader.addDialog.connect(self._on_dialog_loaded)
        # self._loader.start()
        self._load_dialogs()

    def _open_settings(self):
        dialog = None if self.current is None else self.dialogs[self.current]
        window = ChatSettingsWindow(self.sm, self.tm, dialog)
        window.exec()
        window.save()
        if dialog:
            dialog.store()

    def _load_dialogs(self):
        os.makedirs(self._data_path, exist_ok=True)
        for el in os.listdir(self._data_path):
            if el.endswith('.json'):
                dialog = GPTDialog(self._data_path, el[:-len('.json')])
                dialog.load()
                self._add_dialog(dialog)
        if (dialog_id := UUID(self.sm.get('current_dialog', ''))) in self.chat_widgets:
            self._select_dialog(dialog_id)
            self._list_widget.select(dialog_id)

    def _on_dialog_loaded(self, dialog: GPTDialog):
        self._add_dialog(dialog)
        if dialog.id == self._last_dialog:
            self._select_dialog(dialog.id)
            self._list_widget.select(dialog.id)

    def _new_special_dialog(self):
        dialog = GPTDialog(self._data_path)
        dialog.type = GPTDialog.TRANSLATE
        dialog.data['language1'] = 'russian'
        dialog.data['language2'] = 'english'
        dialog.name = f"Переводчик {dialog.data['language1']} ↔ {dialog.data['language2']}"
        dialog.used_messages = 1
        dialog.time = time()
        self._add_dialog(dialog)

    def _new_dialog(self):
        dialog = GPTDialog(self._data_path)
        dialog.time = time()
        self._add_dialog(dialog)

    def _add_dialog(self, dialog):
        self.dialogs[dialog.id] = dialog

        chat_widget = ChatWidget(self.sm, self.tm, dialog)
        chat_widget.buttonBackPressed.connect(self._close_dialog)
        chat_widget.hide()
        self._layout.addWidget(chat_widget, 2)
        self.chat_widgets[dialog.id] = chat_widget
        chat_widget.set_theme()

        self._list_widget.add_item(dialog)

    def _delete_dialog(self, dialog_id):
        if dialog_id == self.current:
            self._close_dialog(dialog_id)
        self.dialogs[dialog_id].delete()
        self.chat_widgets.pop(dialog_id)
        self._list_widget.delete_item(dialog_id)
        self.dialogs.pop(dialog_id)

    def _select_dialog(self, dialog_id):
        if self.current is not None:
            self._close_dialog(self.current)
        self.sm.set('current_dialog', str(dialog_id))
        self.set_list_hidden(self.width() < 400)
        if self.width() >= 400:
            self._list_widget.setMaximumWidth(max(220, self.width() // 3))
        self.chat_widgets[dialog_id].show()
        self.chat_widgets[dialog_id].set_top_hidden(self.width() > 400)
        self.current = dialog_id

    def _close_dialog(self, dialog_id):
        self.chat_widgets[dialog_id].hide()
        self.set_list_hidden(False)
        self._list_widget.setMaximumWidth(10000)
        self._list_widget.deselect(dialog_id)
        self._list_widget.update_item_name(dialog_id)
        self.current = None

    def set_list_hidden(self, hidden):
        for el in [self._button_add, self._button_settings, self._list_widget]:
            el.setHidden(hidden)

    def resizeEvent(self, a0) -> None:
        super().resizeEvent(a0)
        if self.width() > 400:
            self.set_list_hidden(False)
            if self.current is not None:
                self._list_widget.setMaximumWidth(max(220, self.width() // 3))
                self.chat_widgets[self.current].set_top_hidden(True)
            else:
                self._list_widget.setMaximumWidth(10000)
        elif self.current is not None:
            self._list_widget.setMaximumWidth(10000)
            self.set_list_hidden(True)
            self.chat_widgets[self.current].set_top_hidden(False)

    def set_theme(self):
        self._button_add.set_theme()
        self._button_settings.set_theme()
        self._button_add_special.set_theme()
        self._list_widget.set_theme()
        for el in self.chat_widgets.values():
            el.set_theme()


class NewChatDialog(CustomDialog):
    def __init__(self, tm):
        super().__init__(tm, "Новый диалог", True, True)

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        self._labels = []

        label = QLabel("Тип диалога")

        self.set_theme()

    def set_theme(self):
        super().set_theme()


class DialogLoader(QThread):
    addDialog = pyqtSignal(GPTDialog)

    def __init__(self, data_path):
        super().__init__()
        self._data_path = data_path

    def run(self) -> None:
        sleep(1)
        os.makedirs(self._data_path, exist_ok=True)
        for el in os.listdir(self._data_path):
            if el.endswith('.json'):
                dialog = GPTDialog(self._data_path, el[:-len('.json')])
                dialog.load()
                self.addDialog.emit(dialog)
                sleep(0.01)
