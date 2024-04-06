from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import QHBoxLayout
from PyQtUIkit.core import KitFont
from PyQtUIkit.widgets import KitVBoxLayout, KitButton, KitIconButton, KitLabel, KitIconWidget, KitLayoutButton

from src.gpt.chat import GPTChat
from src.gpt.message import GPTMessage


class ReplyList(KitVBoxLayout):
    scrollRequested = pyqtSignal(int)

    def __init__(self, chat: GPTChat, mode=1):
        super().__init__()
        self._chat = chat
        self._mode = mode

        self.setContentsMargins(0, 0, 0, 0)
        self.border = 0

        self._messages = list()
        self.__widgets = dict()

    def add_message(self, message: GPTMessage):
        message_id = message.id
        if message_id in self._messages:
            return

        index = 0
        if self._messages:
            for i in self._chat.message_ids:
                if i == message_id:
                    break
                if i == self._messages[index]:
                    index += 1
                    if index == len(self._messages):
                        break

        self._messages.insert(index, message_id)
        item = _ReplyItem(message, can_be_deleted=self._mode == 1)

        item.deleteRequested.connect(self.delete_item)
        item.scrollRequested.connect(self.scrollRequested.emit)

        item.setMaximumWidth(self.width())
        item.setMinimumWidth(0)
        self.__widgets[message_id] = item
        self.insertWidget(index, item)
        self.show()

    def resizeEvent(self, a0) -> None:
        super().resizeEvent(a0)
        for el in self.__widgets.values():
            el.setMaximumWidth(self.width())

    def delete_item(self, message_id):
        self._messages.remove(message_id)
        self.__widgets[message_id].setParent(None)
        if not self._messages:
            self.hide()

    def clear(self):
        for el in self.__widgets.values():
            el.setParent(None)
        self.__widgets.clear()
        self._messages.clear()
        self.hide()

    @property
    def messages(self):
        for el in self._messages:
            yield el


class _ReplyItem(KitLayoutButton):
    deleteRequested = pyqtSignal(int)
    scrollRequested = pyqtSignal(int)

    def __init__(self, message: GPTMessage, can_be_deleted=True):
        super().__init__()
        self._message = message
        self._can_be_deleted = can_be_deleted
        self.main_palette = 'Transparent'
        self.border = 0
        self.radius = 6
        self.setContentsMargins(4, 2, 2, 2)

        self.setFixedHeight(26)
        self.clicked.connect(lambda: self.scrollRequested.emit(self._message.id))
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        self._icon_widget = KitIconWidget('solid-reply')
        self._icon_widget.setFixedSize(18, 18)
        self.addWidget(self._icon_widget)

        self._label = KitLabel(self._message.content.split('\n')[0])
        self._label.setFixedHeight(16)
        self._label.font_size = KitFont.Size.SMALL
        # self._label.setWordWrap(True)
        self.addWidget(self._label, 1000)

        self._button = KitIconButton('solid-trash')
        self._button.clicked.connect(lambda: self.deleteRequested.emit(self._message.id))
        self._button.size = 22
        self._button.main_palette = 'Bg'
        self._button.border = 0
        self.addWidget(self._button, Qt.AlignmentFlag.AlignRight)
        if not self._can_be_deleted:
            self._button.hide()
