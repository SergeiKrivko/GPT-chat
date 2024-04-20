from PyQt6 import QtGui
from PyQt6.QtCore import pyqtSignal, Qt, QPoint
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QScrollArea, QMenu, QPushButton
from PyQtUIkit.core import KitFont
from PyQtUIkit.themes.locale import KitLocaleString
from PyQtUIkit.widgets import KitScrollArea, KitVBoxLayout, KitButton, KitLabel, KitIconWidget, KitMenu, KitLayoutButton

from src.chat.chat_icon import ChatIcon
from src.gpt.chat import GPTChat


class GPTListWidget(KitScrollArea):
    currentItemChanged = pyqtSignal(int)
    deleteItem = pyqtSignal(int)

    def __init__(self, sm):
        super().__init__()
        self._sm = sm
        self.setMinimumWidth(240)
        self.main_palette = 'Menu'
        self.radius = 0
        # self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._layout = KitVBoxLayout()
        self._layout.spacing = 0
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._layout.padding = 0, 10, 0, 0
        self.setWidget(self._layout)

        self._items = dict()

    def deselect(self, chat_id):
        self._items[chat_id].setChecked(False)

    def select(self, chat_id):
        self._items[chat_id].setChecked(True)
        self._on_item_selected(chat_id)

    def sort_chats(self):
        self._layout.clear()
        items = sorted(self._items.values(), key=lambda item: item.chat.get_sort_key(), reverse=True)
        for el in items:
            self._layout.addWidget(el)
            el.update_name()

    def update_item_name(self, chat_id):
        self._items[chat_id].update_name()

    def _on_item_selected(self, chat_id: int):
        for key, item in self._items.items():
            if key != chat_id:
                item.setChecked(False)
        self.currentItemChanged.emit(chat_id)

    def add_item(self, chat: GPTChat, no_sort=False):
        item = GPTListWidgetItem(self._sm, chat)
        item.selected.connect(self._on_item_selected)
        item.deleteRequested.connect(self.deleteItem)
        item.pinRequested.connect(self.pin_chat)
        chat_id = chat.id
        self._items[chat_id] = item
        self._layout.addWidget(item)
        if not no_sort:
            self._set_items_width()
            self.sort_chats()

    def pin_chat(self, chat_id):
        self.sort_chats()

    def delete_item(self, chat_id):
        self._items[chat_id].setParent(None)
        self._items.pop(chat_id)

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        super().resizeEvent(a0)
        self._set_items_width()

    def _set_items_width(self):
        width = self.width() - 0
        if self.verticalScrollBar().maximum():
            width -= 12
        for el in self._items.values():
            el.setFixedWidth(width)

    def set_theme(self):
        self._tm.auto_css(self, palette='Bg', border=False)


class Label(QLabel):
    mouseMoving = pyqtSignal()

    def __init__(self, text=''):
        super().__init__(text)
        self.setMouseTracking(True)

    def mouseMoveEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.mouseMoving.emit()
        super().mouseMoveEvent(ev)


class GPTListWidgetItem(KitLayoutButton):
    ICON_SIZE = 16

    selected = pyqtSignal(int)
    deleteRequested = pyqtSignal(int)
    pinRequested = pyqtSignal(int)

    def __init__(self, sm, chat: GPTChat):
        super().__init__()
        self._sm = sm
        self.chat = chat
        self._chat_id = chat.id
        self.main_palette = 'Menu'
        self.border = 0
        self.radius = 0
        self.setCheckable(True)
        self.clicked.connect(self._on_clicked)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.run_context_menu)

        self.setFixedHeight(56)
        self.setContentsMargins(12, 5, 12, 5)

        self._icon_widget = ChatIcon(self._sm, self.chat)
        self.addWidget(self._icon_widget)

        layout = KitVBoxLayout()
        layout.setContentsMargins(0, 1, 0, 1)
        layout.setSpacing(0)
        self.addWidget(layout, 100)

        self._name_label = KitLabel()
        layout.addWidget(self._name_label)

        self._last_message_label = KitLabel()
        self._last_message_label.main_palette = 'LastMessage'
        self._last_message_label.font_size = KitFont.Size.SMALL
        self._last_message_label.setWordWrap(True)
        layout.addWidget(self._last_message_label)

        self._right_layout = KitVBoxLayout()
        self._right_layout.setContentsMargins(0, 0, 0, 0)
        self._right_layout.setSpacing(4)
        self.addWidget(self._right_layout)

        self._icon_pinned = KitIconWidget("custom-pin")
        self._icon_pinned.setFixedSize(18, 18)
        self._icon_pinned.setFixedSize(GPTListWidgetItem.ICON_SIZE, GPTListWidgetItem.ICON_SIZE)
        self._right_layout.addWidget(self._icon_pinned)

        self._icon_remote = KitIconWidget("custom-globe")
        self._icon_remote.setFixedSize(18, 18)
        self._icon_remote.setFixedSize(GPTListWidgetItem.ICON_SIZE, GPTListWidgetItem.ICON_SIZE)
        self._right_layout.addWidget(self._icon_remote)

        self.update_name()

    def __str__(self):
        return f"ChatItem({self.chat.id}, {self.chat.get_sort_key()})"

    def update_name(self):
        self._icon_pinned.setHidden(not self.chat.pinned)
        self._icon_remote.setHidden(not self.chat.remote_id)

        if self.chat.name and self.chat.name.strip():
            self._name_label.text = self.chat.name
        else:
            self._name_label.text = KitLocaleString.default_chat_name

        if self.chat.last_message:
            self._last_message_label.text = self.chat.last_message.content
        else:
            self._last_message_label.text = ''

        self._icon_widget.update_icon()

    def run_context_menu(self, pos):
        menu = ContextMenu(self, self.chat)
        menu.move(self.mapToGlobal(pos))
        menu.exec()
        match menu.action:
            case ContextMenu.DELETE:
                self.deleteRequested.emit(self._chat_id)
            case ContextMenu.PIN:
                self.chat.pinned = True
                self.pinRequested.emit(self._chat_id)
            case ContextMenu.UNPIN:
                self.chat.pinned = False
                self.pinRequested.emit(self._chat_id)

    def _on_clicked(self, flag):
        if not flag:
            self.setChecked(True)
        else:
            self.selected.emit(self.chat.id)


class ContextMenu(KitMenu):
    DELETE = 0
    PIN = 1
    UNPIN = 2

    def __init__(self, parent, chat):
        super().__init__(parent)
        self._chat = chat
        self.action = None

        action = self.addAction(KitLocaleString.delete, 'line-trash')
        action.triggered.connect(lambda: self.set_action(ContextMenu.DELETE))

        if self._chat.pinned:
            action = self.addAction(KitLocaleString.unpin, 'custom-unpin')
            action.triggered.connect(lambda: self.set_action(ContextMenu.UNPIN))
        else:
            action = self.addAction(KitLocaleString.pin, 'custom-pin')
            action.triggered.connect(lambda: self.set_action(ContextMenu.PIN))

    def set_action(self, action):
        self.action = action
