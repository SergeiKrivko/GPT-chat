from PyQt6 import QtGui
from PyQt6.QtCore import pyqtSignal, Qt, QPoint
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QScrollArea, QMenu, QPushButton

from src.gpt.chat import GPTChat


class Widget(QWidget):
    mouseMove = pyqtSignal(QPoint)

    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)

    def mouseMoveEvent(self, a0) -> None:
        super().mouseMoveEvent(a0)
        self.mouseMove.emit(a0.pos())


class GPTListWidget(QScrollArea):
    currentItemChanged = pyqtSignal(int)
    deleteItem = pyqtSignal(int)

    def __init__(self, tm):
        super().__init__()
        self._tm = tm
        self.setMinimumWidth(240)
        # self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_widget = Widget()
        self.setWidget(scroll_widget)
        self.setWidgetResizable(True)

        self._layout = QVBoxLayout()
        self._layout.setSpacing(5)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._layout.setContentsMargins(15, 10, 10, 10)
        scroll_widget.setLayout(self._layout)

        self._items = dict()

    def deselect(self, chat_id):
        self._items[chat_id].setChecked(False)

    def select(self, chat_id):
        self._items[chat_id].setChecked(True)
        self._on_item_selected(chat_id)

    def sort_chats(self):
        for el in self._items.values():
            el.setParent(None)
        items = sorted(self._items.values(), key=lambda item: item.chat.get_sort_key(), reverse=True)
        for el in items:
            self._layout.addWidget(el)
            el.update_name()

    def move_to_top(self, chat_id):
        self.sort_chats()
        # item = self._items[chat_id]
        # item.setParent(None)
        # item.update_name()
        # self._layout.insertWidget(0, item)

    def update_item_name(self, chat_id):
        self._items[chat_id].update_name()

    def _on_item_selected(self, chat_id: int):
        for key, item in self._items.items():
            if key != chat_id:
                item.setChecked(False)
        self.currentItemChanged.emit(chat_id)

    def add_item(self, chat: GPTChat):
        item = GPTListWidgetItem(self._tm, chat)
        item.selected.connect(self._on_item_selected)
        item.deleteRequested.connect(self.deleteItem)
        item.pinRequested.connect(self.pin_chat)
        chat_id = chat.id
        item.set_theme()
        self._items[chat_id] = item
        self._layout.addWidget(item)
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
        width = self.width() - 30
        if self.verticalScrollBar().maximum():
            width -= 8
        for el in self._items.values():
            el.setFixedWidth(width)

    def set_theme(self):
        self._tm.auto_css(self, palette='Bg', border=False)
        for item in self._items.values():
            item.set_theme()


class Label(QLabel):
    mouseMoving = pyqtSignal()

    def __init__(self, text=''):
        super().__init__(text)
        self.setMouseTracking(True)

    def mouseMoveEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.mouseMoving.emit()
        super().mouseMoveEvent(ev)


class GPTListWidgetItem(QPushButton):
    PALETTE = 'Bg'
    ICON_SIZE = 16

    selected = pyqtSignal(int)
    deleteRequested = pyqtSignal(int)
    pinRequested = pyqtSignal(int)

    def __init__(self, tm, chat: GPTChat):
        super().__init__()
        self._tm = tm
        self.chat = chat
        self._chat_id = chat.id
        # self.setMouseTracking(True)
        self.setCheckable(True)
        self.clicked.connect(self._on_clicked)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.run_context_menu)

        self.setFixedHeight(44)

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(7, 7, 7, 7)
        self.setLayout(main_layout)

        self._icon_label = Label()
        self._icon_label.setFixedSize(24, 24)
        main_layout.addWidget(self._icon_label)

        self._name_label = Label()
        self._name_label.setWordWrap(True)
        main_layout.addWidget(self._name_label)

        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addLayout(right_layout)

        self._icon_pinned = Label()
        self._icon_pinned.setFixedSize(GPTListWidgetItem.ICON_SIZE, GPTListWidgetItem.ICON_SIZE)
        right_layout.addWidget(self._icon_pinned)

        self._icon_remote = Label()
        self._icon_remote.setFixedSize(GPTListWidgetItem.ICON_SIZE, GPTListWidgetItem.ICON_SIZE)
        right_layout.addWidget(self._icon_remote)

        self.update_name()

    def __str__(self):
        return f"ChatItem({self.chat.id}, {self.chat.get_sort_key()})"

    def update_name(self):
        icons = {
            GPTChat.SIMPLE: 'simple_chat',
            GPTChat.TRANSLATE: 'translate',
            GPTChat.SUMMARY: 'summary',
        }
        self._icon_label.setPixmap(QPixmap(self._tm.get_image(
            icons.get(self.chat.type, 'simple_chat'))).scaledToWidth(24))

        self._icon_pinned.setHidden(not self.chat.pinned)
        self._icon_remote.setHidden(not self.chat.remote_id)

        if self.chat.name and self.chat.name.strip():
            self._name_label.setText(self.chat.name)
        elif self.chat.last_message:
            self._name_label.setText(self.chat.last_message.content)
        else:
            self._name_label.setText('<Новый диалог>')

    def run_context_menu(self, pos):
        menu = ContextMenu(self._tm, self.chat)
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

    def set_theme(self):
        self._tm.auto_css(self, palette=GPTListWidgetItem.PALETTE, border=False)
        self._name_label.setStyleSheet("background: transparent; border: none;")
        self._name_label.setFont(self._tm.font_medium)
        self._icon_label.setStyleSheet("background: transparent; border: none;")
        self._icon_pinned.setStyleSheet("background: transparent; border: none;")
        self._icon_remote.setStyleSheet("background: transparent; border: none;")
        self.update_name()
        self._icon_pinned.setPixmap(QPixmap(self._tm.get_image('pin')).scaled(
            GPTListWidgetItem.ICON_SIZE, GPTListWidgetItem.ICON_SIZE))
        self._icon_remote.setPixmap(QPixmap(self._tm.get_image('remote')).scaled(
            GPTListWidgetItem.ICON_SIZE, GPTListWidgetItem.ICON_SIZE))


class ContextMenu(QMenu):
    DELETE = 0
    PIN = 1
    UNPIN = 2

    def __init__(self, tm, chat):
        super().__init__()
        self.tm = tm
        self._chat = chat
        self.action = None

        action = self.addAction(QIcon(self.tm.get_image('button_delete')), "Удалить")
        action.triggered.connect(lambda: self.set_action(ContextMenu.DELETE))

        if self._chat.pinned:
            action = self.addAction(QIcon(self.tm.get_image('unpin')), "Открепить")
            action.triggered.connect(lambda: self.set_action(ContextMenu.UNPIN))
        else:
            action = self.addAction(QIcon(self.tm.get_image('pin')), "Закрепить")
            action.triggered.connect(lambda: self.set_action(ContextMenu.PIN))

        self.tm.auto_css(self)

    def set_action(self, action):
        self.action = action
