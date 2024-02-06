import shutil
from time import sleep

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QHBoxLayout, QWidget, QVBoxLayout, QMenu, QPushButton
from qasync import asyncSlot

from src.chat.chat_widget import ChatWidget
from src.chat.chats_list import GPTListWidget
from src.chat.settings_window import ChatSettingsWindow
from src.database import ChatManager
from src.gpt.chat import GPTChat
from src.settings_manager import SettingsManager
from src.ui.authentication_window import AuthenticationWindow
from src.ui.button import Button
from src.ui.custom_dialog import ask


class ChatPanel(QWidget):
    WIDTH = 550

    def __init__(self, sm: SettingsManager, tm, chat_manager: ChatManager):
        super().__init__()
        self.sm = sm
        self.tm = tm
        self._chat_manager = chat_manager
        self._chat_manager.newChat.connect(self._add_chat)
        self._chat_manager.deleteChat.connect(self._on_chat_deleted)
        self._chat_manager.deleteRemoteChat.connect(self._on_remote_chat_deleted)
        # self._chat_manager.updateChat.connect(self._list_widget.sort_chats)
        self._chat_manager.newMessage.connect(self._on_new_message)
        self._chat_manager.deleteMessage.connect(self._on_delete_message)

        self._layout = QHBoxLayout()
        self._layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._layout.setContentsMargins(10, 10, 0, 10)
        self.setLayout(self._layout)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        self._layout.addLayout(main_layout, 0)

        top_layout = QHBoxLayout()
        top_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        main_layout.addLayout(top_layout)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        top_layout.addLayout(layout)

        self._button_add = Button(self.tm, 'plus', css='Bg')
        self._button_add.setFixedSize(36, 36)
        self._button_add.clicked.connect(lambda: self._new_chat())
        layout.addWidget(self._button_add)

        self._button_add_special = QPushButton()
        self._button_add_special.setFixedSize(20, 36)
        self._button_add_special.setMenu(NewChatMenu(self.tm, self._new_chat))
        layout.addWidget(self._button_add_special)

        self._button_settings = Button(self.tm, 'generate', css='Bg')
        self._button_settings.setFixedSize(36, 36)
        self._button_settings.clicked.connect(self._open_settings)
        top_layout.addWidget(self._button_settings)

        self._button_user = Button(self.tm, 'user', css='Bg')
        self._button_user.setFixedSize(36, 36)
        self._button_user.clicked.connect(self._open_user_window)
        top_layout.addWidget(self._button_user)

        self._list_widget = GPTListWidget(tm)
        main_layout.addWidget(self._list_widget)
        self._list_widget.deleteItem.connect(self._delete_chat)
        self._list_widget.currentItemChanged.connect(self._select_chat)

        self.chats = dict()
        self.chat_widgets = dict()
        self.current = None

        try:
            self._last_chat = int(self.sm.get('current_dialog', ''))
        except ValueError:
            self._last_chat = None

    def _open_settings(self):
        chat = None if self.current is None else self.chats[self.current]
        window = ChatSettingsWindow(self.sm, self.tm, self._chat_manager, chat)
        window.exec()
        window.save()

    def _open_user_window(self):
        uid = self.sm.get('user_id')
        window = AuthenticationWindow(self.sm, self.tm)
        window.exec()
        if uid != self.sm.get('user_id'):
            self._clear_chats()
            self._clear_chats()
            self._chat_manager.auth()

    def _clear_chats(self):
        self._close_chat(self.current)
        for el in self.chats:
            self._list_widget.delete_item(el)
        self.chats.clear()
        for el in self.chat_widgets.values():
            el.setParent(None)
        self.chat_widgets.clear()

    def _on_remote_chat_deleted(self, chat):
        if not chat:
            return
        if ask(self.tm, f"Синхронизация чата {chat.name} была прекращена. Удалить локальную копию чата?",
               default='Нет') == 'Да':
            self._delete_chat(chat.id)
        else:
            self._chat_manager.make_remote(chat, False)

    def _on_chat_loaded(self, chat: GPTChat):
        self._add_chat(chat)
        if chat.id == self._last_chat:
            self._list_widget.select(chat.id)

    def _new_chat(self, chat_type=GPTChat.SIMPLE):
        self._chat_manager.new_chat(chat_type)

    def _add_chat(self, chat):
        self.chats[chat.id] = chat

        chat_widget = ChatWidget(self.sm, self.tm, self._chat_manager, chat)
        chat_widget.buttonBackPressed.connect(self._close_chat)
        chat_widget.hide()
        chat_widget.updated.connect(lambda: self._list_widget.move_to_top(chat.id))
        self._layout.addWidget(chat_widget, 2)
        self.chat_widgets[chat.id] = chat_widget
        chat_widget.set_theme()

        self._list_widget.add_item(chat)

    def _delete_chat(self, chat_id):
        if chat_id == self.current:
            self._close_chat(chat_id)
        self._chat_manager.delete_chat(chat_id)

    def _on_chat_deleted(self, chat_id):
        if chat_id == self.current:
            self._close_chat(chat_id)
        self.chat_widgets.pop(chat_id)
        self._list_widget.delete_item(chat_id)
        self.chats.pop(chat_id)

    def _select_chat(self, chat_id):
        if self.current is not None:
            self._close_chat(self.current)
        self.sm.set('current_dialog', str(chat_id))
        self.chat_widgets[chat_id].show()
        self.current = chat_id
        self._resize()
        # if self.sm.authorized:
        #     self._pull_chat(chat_id)

    def _on_new_message(self, chat_id, message):
        self.chat_widgets[chat_id].add_message(message)

    def _on_delete_message(self, chat_id, message):
        self.chat_widgets[chat_id].delete_message(message.id)

    @asyncSlot()
    async def _pull_chat(self, chat_id):
        chat = self.chats[chat_id]
        for message in await chat.pull():
            self.chat_widgets[chat.id].add_bubble(message)

    def _close_chat(self, chat_id):
        if chat_id not in self.chats:
            return
        self.chat_widgets[chat_id].hide()
        self.set_list_hidden(False)
        self.current = None
        self._resize()
        self._list_widget.deselect(chat_id)
        self._list_widget.update_item_name(chat_id)
        self.sm.set('current_dialog', '')

    def set_list_hidden(self, hidden):
        for el in [self._button_add, self._button_add_special, self._button_settings, self._list_widget,
                   self._button_user]:
            el.setHidden(hidden)

    def _resize(self):
        if self.width() > 550:
            self.set_list_hidden(False)
            if self.current is not None:
                self.chat_widgets[self.current].set_top_hidden(True)
            self._list_widget.setFixedWidth(max(220, self.width() // 4))
            # else:
            #     self._list_widget.setMaximumWidth(10000)
        elif self.current is not None:
            self.set_list_hidden(True)
            self.chat_widgets[self.current].set_top_hidden(False)
        else:
            self.set_list_hidden(False)
            self._list_widget.setMaximumWidth(10000)

    def resizeEvent(self, a0) -> None:
        super().resizeEvent(a0)
        self._resize()

    def closeEvent(self, a0) -> None:
        super().closeEvent(a0)
        self.db.commit()
        try:
            shutil.rmtree(f"{self.sm.app_data_dir}/temp")
        except Exception:
            pass

    def set_theme(self):
        self._button_add.set_theme()
        self._button_settings.set_theme()
        self._button_user.set_theme()
        self.tm.auto_css(self._button_add_special, palette='Bg', border=False)
        self._list_widget.set_theme()
        for el in self.chat_widgets.values():
            el.set_theme()


class NewChatMenu(QMenu):
    def __init__(self, tm, func):
        super().__init__()
        self.tm = tm
        self.func = func

        action = self.addAction(QIcon(self.tm.get_image('simple_chat')), "Обычный диалог")
        action.triggered.connect(lambda: func(GPTChat.SIMPLE))

        action = self.addAction(QIcon(self.tm.get_image('translate')), "Переводчик")
        action.triggered.connect(lambda: func(GPTChat.TRANSLATE))

        action = self.addAction(QIcon(self.tm.get_image('summary')), "Краткое содержание")
        action.triggered.connect(lambda: func(GPTChat.SUMMARY))

        self.tm.auto_css(self)
        self.tm.themeChanged.connect(lambda: self.tm.auto_css(self))


class ChatLoader(QThread):
    addChat = pyqtSignal(GPTChat)

    def __init__(self, chats: list[GPTChat], first=None):
        super().__init__()
        self._chats: chats = chats
        self._first = first

    def run(self) -> None:
        for c in self._chats:
            self.addChat.emit(c)
            sleep(0.1)
