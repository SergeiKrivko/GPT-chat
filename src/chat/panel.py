import asyncio
import shutil
from time import sleep

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQtUIkit.widgets import KitHBoxLayout, KitVBoxLayout, KitIconButton, KitHGroup, KitMenu, KitDialog
from qasync import asyncSlot

from src.chat.chat_widget import ChatWidget
from src.chat.chats_list import GPTListWidget
from src.chat.render_latex import rerender_all
from src.chat.settings_window import ChatSettingsWindow
from src.database import ChatManager
from src.gpt.chat import GPTChat
from src.settings_manager import SettingsManager
from src.ui.authentication_window import AuthenticationWindow


class ChatPanel(KitHBoxLayout):
    WIDTH = 550

    def __init__(self, sm: SettingsManager, chat_manager: ChatManager, um):
        super().__init__()
        self.sm = sm
        self._um = um
        self._chat_manager = chat_manager
        self._chat_manager.newChat.connect(self._add_chat)
        self._chat_manager.newChats.connect(self._add_chats)
        self._chat_manager.deleteChat.connect(self._on_chat_deleted)
        self._chat_manager.deleteRemoteChat.connect(self._on_remote_chat_deleted)
        # self._chat_manager.updateChat.connect(self._list_widget.sort_chats)
        self._chat_manager.newMessage.connect(self._on_new_message)
        self._chat_manager.deleteMessage.connect(self._on_delete_message)

        self.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setContentsMargins(0, 0, 0, 0)

        self._main_layout = KitVBoxLayout()
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)
        self.addWidget(self._main_layout, 0)

        self._top_layout = KitHBoxLayout()
        self._top_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._top_layout.setContentsMargins(8, 8, 8, 8)
        self._main_layout.addWidget(self._top_layout)

        self._button_add = KitIconButton('solid-plus')
        self._button_add.size = 36
        self._button_add.border = 0
        self._button_add.setContentsMargins(3, 3, 3, 3)
        self._button_add.main_palette = 'Bg'
        self._button_add.clicked.connect(lambda: self._new_chat())
        self._top_layout.addWidget(self._button_add)

        self._button_settings = KitIconButton('solid-gear')
        self._button_settings.size = 36
        self._button_settings.setContentsMargins(3, 3, 3, 3)
        self._button_settings.main_palette = 'Bg'
        self._button_settings.border = 0
        self._button_settings.clicked.connect(self._open_settings)
        self._top_layout.addWidget(self._button_settings)

        self._button_user = KitIconButton('solid-user')
        self._button_user.size = 36
        self._button_user.setContentsMargins(3, 3, 3, 3)
        self._button_user.main_palette = 'Bg'
        self._button_user.border = 0
        self._button_user.clicked.connect(self._open_user_window)
        self._top_layout.addWidget(self._button_user)

        self._button_search = KitIconButton('solid-magnifying-glass')
        self._button_search.size = 36
        self._button_search.setContentsMargins(3, 3, 3, 3)
        self._button_search.main_palette = 'Bg'
        self._button_search.border = 0
        self._button_search.clicked.connect(self._show_search)
        self._button_search.setCheckable(True)
        self._top_layout.addWidget(self._button_search)

        self._top_layout.addWidget(KitHBoxLayout(), 1000)

        self._list_widget = GPTListWidget()
        self._main_layout.addWidget(self._list_widget)
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
        window = ChatSettingsWindow(self, self.sm, self._chat_manager, self._um, chat)
        window.exec()
        window.save()
        self._update_chats()

    @asyncSlot()
    async def _update_chats(self):
        await asyncio.sleep(0.1)
        self._list_widget.sort_chats()

    def _open_user_window(self):
        uid = self.sm.get('user_id')
        window = AuthenticationWindow(self, self.sm)
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
        if KitDialog.question(self, f"Синхронизация чата {chat.name} была прекращена. Удалить локальную копию чата?",
                              ('Нет', 'Да'), default='Нет') == 'Да':
            self._delete_chat(chat.id)
        else:
            self._chat_manager.make_remote(chat, False)
            self._list_widget.sort_chats()

    def _on_chat_loaded(self, chat: GPTChat):
        self._add_chat(chat)
        if chat.id == self._last_chat:
            self._list_widget.select(chat.id)

    def _new_chat(self, chat_type=GPTChat.SIMPLE):
        self._chat_manager.new_chat(chat_type)

    def _add_chat(self, chat, no_sort=False):
        self.chats[chat.id] = chat

        chat_widget = ChatWidget(self.sm, self._chat_manager, self._um, chat)
        chat_widget.buttonBackPressed.connect(self._close_chat)
        chat_widget.hide()
        chat_widget.updated.connect(lambda: self._list_widget.move_to_top(chat.id))
        self.addWidget(chat_widget, 2)
        self.chat_widgets[chat.id] = chat_widget

        self._list_widget.add_item(chat, no_sort=no_sort)

    def _add_chats(self, chats: list):
        for i in range(len(chats) - 1):
            self._add_chat(chats[i], no_sort=True)
        if chats:
            self._add_chat(chats[-1])

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
        self._button_search.setChecked(self.chat_widgets[chat_id].search_active)
        self._resize()

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
        self._main_layout.setHidden(hidden)

    def _resize(self):
        if self.width() > 550:
            self.set_list_hidden(False)
            if self.current is not None:
                self.chat_widgets[self.current].set_top_hidden(True)
            self._list_widget.setFixedWidth(max(250, self.width() // 4))
            self._button_search.show()
        elif self.current is not None:
            self.set_list_hidden(True)
            self.chat_widgets[self.current].set_top_hidden(False)
        else:
            self.set_list_hidden(False)
            self._button_search.hide()
            self._list_widget.setMaximumWidth(10000)

    def _show_search(self):
        if self.current is not None:
            self.chat_widgets[self.current].show_search(self._button_search.isChecked())

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

    def _apply_theme(self):
        rerender_all(self._tm)
        super()._apply_theme()
