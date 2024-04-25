import shutil

from PyQt6.QtCore import Qt
from PyQtUIkit.core import KitFont
from PyQtUIkit.themes.locale import KitLocaleString
from PyQtUIkit.widgets import KitHBoxLayout, KitVBoxLayout, KitIconButton, KitDialog, KitVSeparator, KitLabel, \
    KitIconWidget, KitTabLayout
from qasync import asyncSlot

from src.chat.chat_widget import ChatWidget
from src.chat.chats_list import GPTListWidget
from src.chat.render_latex import rerender_all
from src.chat.wallpapers import WallpaperWidget
from src.gpt.check_providers import CheckModelsService
from src.ui.settings_window import SettingsWindow
from src.database import ChatManager
from src.gpt.chat import GPTChat
from src.settings_manager import SettingsManager
from src.auth.authentication_window import AuthenticationWindow


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

        self._check_model_service = CheckModelsService(self.sm)

        self._main_layout = KitVBoxLayout()
        self.addWidget(self._main_layout, 1)

        top_layout = KitHBoxLayout()
        top_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        top_layout.padding = 8
        top_layout.setSpacing(4)
        self._main_layout.addWidget(top_layout)

        self._button_add = KitIconButton('line-add')
        self._button_add.size = 36
        self._button_add.border = 0
        self._button_add.main_palette = 'Bg'
        self._button_add.clicked.connect(self._new_chat)
        top_layout.addWidget(self._button_add)

        self._button_archive = KitIconButton('line-archive')
        self._button_archive.size = 36
        self._button_archive.main_palette = 'Bg'
        self._button_archive.border = 0
        self._button_archive.setCheckable(True)
        self._button_archive.on_click = lambda flag: self._folders_layout.setCurrent(1 if flag else 0)
        top_layout.addWidget(self._button_archive)

        top_layout.addWidget(KitHBoxLayout(), 100)

        self._button_user = KitIconButton('line-person')
        self._button_user.size = 36
        self._button_user.main_palette = 'Bg'
        self._button_user.border = 0
        self._button_user.clicked.connect(self._open_user_window)
        top_layout.addWidget(self._button_user)

        self._button_settings = KitIconButton('line-settings')
        self._button_settings.size = 36
        self._button_settings.main_palette = 'Bg'
        self._button_settings.border = 0
        self._button_settings.clicked.connect(self._open_settings)
        top_layout.addWidget(self._button_settings)

        self._folders_layout = KitTabLayout()
        self._main_layout.addWidget(self._folders_layout)

        self._folders = list()
        for i in range(2):
            list_widget = GPTListWidget(self.sm)
            self._folders.append(list_widget)
            self._folders_layout.addWidget(list_widget)
            list_widget.deleteItem.connect(self._delete_chat)
            list_widget.currentItemChanged.connect(self._select_chat)
            list_widget.moveToFolderRequested.connect(self._move_chat)

        self._separator = KitVSeparator()
        self.addWidget(self._separator)

        layout = KitVBoxLayout()
        layout.main_palette = 'Chat'
        self.addWidget(layout)

        self._chats_layout = WallpaperWidget()
        layout.addWidget(self._chats_layout)
        self._set_wallpaper(self.sm.get('wallpaper', 0))

        self._no_chat_widget = KitVBoxLayout()
        self._no_chat_widget.alignment = Qt.AlignmentFlag.AlignCenter
        self._chats_layout.addWidget(self._no_chat_widget)
        self._no_chat_widget.addWidget(KitVBoxLayout(), 100)

        icon_widget = KitIconWidget('line-chatbubbles')
        icon_widget.setFixedHeight(300)
        icon_widget.setMaximumWidth(300)
        self._no_chat_widget.addWidget(icon_widget)

        label = KitLabel(KitLocaleString.select_chat)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.font_size = KitFont.Size.SUPER_BIG
        label.font = 'bold'
        self._no_chat_widget.addWidget(label)
        self._no_chat_widget.addWidget(KitVBoxLayout(), 100)

        self.chats = dict()
        self.chat_widgets = dict()
        self.current = None

        self._settings_window = SettingsWindow(self, self.sm, self._chat_manager, self._um)
        self._settings_window.wallpaperChanged.connect(self._set_wallpaper)

        try:
            self._last_chat = int(self.sm.get('current_dialog', ''))
        except ValueError:
            self._last_chat = None

    def _set_wallpaper(self, index):
        if index == 0:
            self._chats_layout.set_wallpaper(None)
        else:
            self._chats_layout.set_wallpaper(f'pattern-{index}')
        self._chats_layout.update()

    def _open_settings(self):
        self._settings_window.exec()
        self._settings_window.save()

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
        for el in self._folders:
            el.clear()
        self.chats.clear()
        for el in self.chat_widgets.values():
            el.setParent(None)
        self.chat_widgets.clear()

    def _on_remote_chat_deleted(self, chat: GPTChat):
        if not chat:
            return
        if KitDialog.question(self, f"Синхронизация чата {chat.name} была прекращена. Удалить локальную копию чата?",
                              ('Нет', 'Да'), default='Нет') == 'Да':
            self._delete_chat(chat.id)
        else:
            self._chat_manager.make_remote(chat, False)
            self._folders[chat.folder].sort_chats()

    def _on_chat_loaded(self, chat: GPTChat):
        self._add_chat(chat)
        if chat.id == self._last_chat:
            self._folders[chat.folder].select(chat.id)

    def _new_chat(self):
        self._chat_manager.new_chat()
        self._folders_layout.setCurrent(0)
        self._button_archive.setChecked(False)

    def _add_chat(self, chat, no_sort=False):
        self.chats[chat.id] = chat

        chat_widget = ChatWidget(self.sm, self._chat_manager, chat)
        chat_widget.buttonBackPressed.connect(self._close_chat)
        chat_widget.hide()
        chat_widget.updated.connect(self._folders[chat.folder].sort_chats)
        self._chats_layout.addWidget(chat_widget, 2)
        self.chat_widgets[chat.id] = chat_widget

        self._folders[chat.folder].add_item(chat, no_sort=no_sort)

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
        self._chats_layout.deleteWidget(self.chat_widgets[chat_id])
        self.chat_widgets.pop(chat_id)
        for folder in self._folders:
            folder.delete_item(chat_id)

    def _select_chat(self, chat_id):
        if self.current is not None:
            self._close_chat(self.current)
        self.sm.set('current_dialog', str(chat_id))
        self._no_chat_widget.hide()
        self.chat_widgets[chat_id].show()
        self.current = chat_id
        self._resize()

    def _move_chat(self, chat_id, folder):
        chat = self.chats[chat_id]
        self._folders[chat.folder].delete_item(chat_id)
        chat.folder = folder
        self._folders[chat.folder].add_item(chat)

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
        self._folders[self.chats[chat_id].folder].deselect(chat_id)
        self._folders[self.chats[chat_id].folder].update_item_name(chat_id)
        self.sm.set('current_dialog', '')

    def set_list_hidden(self, hidden):
        self._main_layout.setHidden(hidden)

    def _resize(self):
        if self.width() > 550:
            self._separator.show()
            self.set_list_hidden(False)
            self._chats_layout.show()
            if self.current is not None:
                self.chat_widgets[self.current].set_top_hidden(True)
            else:
                self._no_chat_widget.show()
            self._main_layout.setFixedWidth(max(250, self.width() // 4))
        elif self.current is not None:
            self._separator.hide()
            self.set_list_hidden(True)
            self._chats_layout.show()
            self.chat_widgets[self.current].set_top_hidden(False)
        else:
            self._separator.hide()
            self._no_chat_widget.hide()
            self._chats_layout.hide()
            self.set_list_hidden(False)
            self._main_layout.setMaximumWidth(10000)

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
