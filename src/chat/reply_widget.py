from uuid import UUID

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QLabel

from src.gpt.chat import GPTChat
from src.gpt.message import GPTMessage
from src.ui.button import Button


class ReplyList(QVBoxLayout):
    def __init__(self, tm, chat: GPTChat):
        super().__init__()
        self._tm = tm
        self._chat = chat

        self._messages = list()
        self._widgets = dict()

    def add_message(self, message_id: UUID):
        if message_id in self._messages:
            return

        index = 0
        if self._messages:
            for i in self._chat.messages_order:
                if i == message_id:
                    break
                if i == self._messages[index]:
                    index += 1
                    if index == len(self._messages):
                        break

        self._messages.insert(index, message_id)
        item = _ReplyItem(self._tm, self._chat.messages[message_id])
        item.deleteRequested.connect(self.delete_item)
        self._widgets[message_id] = item
        self.insertWidget(index, item)

    def delete_item(self, message_id):
        self._messages.remove(message_id)
        self._widgets[message_id].setParent(None)

    def clear(self):
        for el in self._widgets.values():
            el.setParent(None)
        self._widgets.clear()
        self._messages.clear()

    @property
    def messages(self):
        for el in self._messages:
            yield el


class _ReplyItem(QWidget):
    deleteRequested = pyqtSignal(UUID)

    def __init__(self, tm, message: GPTMessage):
        super().__init__()
        self._message = message
        self._tm = tm

        strange_layout = QHBoxLayout()
        strange_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(strange_layout)
        strange_widget = QWidget()
        strange_layout.addWidget(strange_widget)

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(2, 2, 2, 2)
        strange_widget.setLayout(main_layout)

        self._icon = QLabel()
        self._icon.setPixmap(QPixmap(self._tm.get_image('reply')))
        self._icon.setFixedSize(18, 18)
        main_layout.addWidget(self._icon)

        self._label = QLabel(self._message.content.split('\n')[0])
        self._label.setFixedHeight(16)
        self._label.setWordWrap(True)
        main_layout.addWidget(self._label)

        self._button = Button(self._tm, 'button_delete')
        self._button.clicked.connect(lambda: self.deleteRequested.emit(self._message.id))
        self._button.setFixedSize(22, 22)
        main_layout.addWidget(self._button)

        self.set_theme()

    def set_theme(self):
        self.setStyleSheet(self._tm.base_css(palette='Main', border=False))
        for el in [self._button, self._label]:
            self._tm.auto_css(el)
