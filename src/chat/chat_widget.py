from time import sleep
from uuid import UUID

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QVBoxLayout, QScrollArea, QWidget, QHBoxLayout, QTextEdit, QLabel

from src import gpt
from src.chat.reply_widget import ReplyList
from src.gpt.chat import GPTChat
from src.chat.chat_bubble import ChatBubble
from src.chat.settings_window import ChatSettingsWindow
from src.gpt.message import GPTMessage
from src.ui.button import Button
from src.ui.message_box import MessageBox


class ChatWidget(QWidget):
    buttonBackPressed = pyqtSignal(UUID)
    updated = pyqtSignal()

    def __init__(self, sm, tm, chat: GPTChat):
        super().__init__()
        self._sm = sm
        self._tm = tm
        self._chat = chat

        self._bubbles = dict()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 10, 0)
        self.setLayout(layout)

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top_layout)

        self._button_back = Button(self._tm, 'button_back', css='Bg')
        self._button_back.setFixedSize(36, 36)
        self._button_back.clicked.connect(lambda: self.buttonBackPressed.emit(self._chat.id))
        top_layout.addWidget(self._button_back)

        self._name_label = QLabel(chat.name if chat.name.strip() else 'Диалог')
        top_layout.addWidget(self._name_label)

        self._button_settings = Button(self._tm, 'generate', css='Bg')
        self._button_settings.setFixedSize(36, 36)
        self._button_settings.clicked.connect(self._open_settings)
        top_layout.addWidget(self._button_settings)

        self._scroll_area = QScrollArea()
        layout.addWidget(self._scroll_area, 1)

        self._scroll_widget = _ScrollWidget()
        self._scroll_widget.resized.connect(self._scroll)
        self._scroll_area.setWidget(self._scroll_widget)
        self._scroll_area.verticalScrollBar().valueChanged.connect(self._on_scrolled)
        self._scroll_area.setWidgetResizable(True)

        scroll_layout = QVBoxLayout()
        self._scroll_area.setLayout(scroll_layout)
        scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._scroll_layout = QVBoxLayout()
        self._scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._scroll_layout.setContentsMargins(0, 0, 0, 0)
        self._scroll_widget.setLayout(scroll_layout)
        scroll_layout.addLayout(self._scroll_layout)

        self._progress_marker = QLabel("GPT печатает...")
        scroll_layout.addWidget(self._progress_marker)
        self._progress_marker.hide()

        self._reply_list = ReplyList(self._tm, self._chat)
        self._reply_list.scrollRequested.connect(self.scroll_to_message)
        layout.addWidget(self._reply_list)

        bottom_layout = QHBoxLayout()
        layout.addLayout(bottom_layout)

        self._text_edit = ChatInputArea()
        self._text_edit.returnPressed.connect(self.send_message)
        bottom_layout.addWidget(self._text_edit, 1)

        self._button = Button(self._tm, "button_send", css='Bg')
        self._button.setFixedSize(30, 30)
        self._button.clicked.connect(self.send_message)
        bottom_layout.addWidget(self._button)

        self.looper = None
        self._last_bubble = None
        self._last_message = None
        self._to_bottom = True
        self._messages_is_loaded = False

    def _load_messages(self):
        self._messages_is_loaded = True
        loader = MessageLoader(self._chat)
        loader.messageLoaded.connect(self.insert_bubble)
        self._sm.run_process(loader, f"load-{self._chat.id}")

    def send_message(self):
        if not ((text := self._text_edit.toPlainText()).strip()):
            return
        self.add_bubble(self._chat.append_message('user', text, tuple(self._reply_list.messages)))
        self._text_edit.setText("")

        messages = self._chat.messages_to_prompt(list(self._reply_list.messages))
        self._reply_list.clear()

        self.looper = Looper(messages, self._chat, temperature=self._chat.temperature)
        if isinstance(self.looper, Looper) and not self.looper.isFinished():
            self.looper.terminate()
        self._last_message = None
        self._progress_marker.show()
        self.looper.sendMessage.connect(self.add_text)
        self.looper.exception.connect(self._on_gpt_error)
        self.looper.finished.connect(self._progress_marker.hide)
        self.looper.start()

    def add_bubble(self, message: GPTMessage):
        bubble = ChatBubble(self._sm, self._tm,self._chat, message)
        self._add_bubble(bubble)
        return bubble

    def insert_bubble(self, message: GPTMessage):
        bubble = ChatBubble(self._sm, self._tm, self._chat, message)
        self._add_bubble(bubble, 0)
        return bubble

    def set_top_hidden(self, hidden):
        for el in [self._name_label, self._button_settings, self._button_back]:
            el.setHidden(hidden)

    def _add_bubble(self, bubble, index=None):
        bubble.deleteRequested.connect(lambda: self._delete_message(bubble.message.id))
        bubble.replyRequested.connect(lambda: self._reply_list.add_message(bubble.message.id))
        bubble.scrollRequested.connect(self.scroll_to_message)
        if index is None:
            self.updated.emit()
            self._scroll_layout.addWidget(bubble)
            self._bubbles[bubble.message.id] = bubble
        else:
            self._scroll_layout.insertWidget(index, bubble)
            self._bubbles[bubble.message.id] = bubble
        bubble.set_theme()

    def _delete_message(self, message_id):
        self._chat.pop_message(message_id)
        self._bubbles.pop(message_id).setParent(None)

    def add_text(self, text):
        if self._last_message is None:
            self._last_message = self._chat.append_message('assistant', text)
            self._last_bubble = self.add_bubble(self._last_message)
        else:
            self._last_bubble.add_text(text)
        self._chat.store()

    def scroll_to_message(self, message_id):
        self._scroll_area.verticalScrollBar().setValue(self._bubbles[message_id].pos().y() - 5)

    def _on_scrolled(self):
        self._to_bottom = abs(self._scroll_area.verticalScrollBar().maximum() -
                              self._scroll_area.verticalScrollBar().value()) < 5
        self._chat.scrolling_pos = self._scroll_area.verticalScrollBar().value()

    def _scroll(self):
        if self._to_bottom:
            self._scroll_area.verticalScrollBar().setValue(self._scroll_area.verticalScrollBar().maximum())

    def showEvent(self, a0) -> None:
        super().showEvent(a0)
        if not self._messages_is_loaded:
            self._load_messages()
        self._scroll_area.verticalScrollBar().setValue(self._chat.scrolling_pos)

    def _open_settings(self):
        dialog = ChatSettingsWindow(self._sm, self._tm, self._chat)
        dialog.exec()
        dialog.save()
        self._chat.store()
        self._name_label.setText(self._chat.name if self._chat.name.strip() else 'Диалог')

    def _on_gpt_error(self, ex):
        MessageBox(MessageBox.Icon.Warning, "Ошибка", f"{ex.__class__.__name__}: {ex}", self._tm)

    def set_theme(self):
        self._scroll_widget.setStyleSheet(self._tm.base_css(palette='Main', border=False))
        for el in [self._scroll_area, self._text_edit, self._button, self._button_back, self._name_label,
                   self._button_settings]:
            self._tm.auto_css(el)
        for el in self._bubbles:
            el.set_theme()


class Looper(QThread):
    sendMessage = pyqtSignal(str)
    exception = pyqtSignal(Exception)

    def __init__(self, text, chat, **kwargs):
        super().__init__()
        self.text = text
        self.chat = chat
        self.kwargs = kwargs

    def run(self):
        try:
            for el in gpt.stream_response(self.text, model=self.chat.model, **self.kwargs):
                self.sendMessage.emit(el)
        except Exception as ex:
            self.exception.emit(ex)


class ChatInputArea(QTextEdit):
    returnPressed = pyqtSignal()
    resize = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setFixedHeight(30)
        self.textChanged.connect(self._on_text_changed)

        self._shift_pressed = False

    def _on_text_changed(self):
        height = self.verticalScrollBar().maximum()
        if not height:
            self.setFixedHeight(30)
            height = self.verticalScrollBar().maximum()
        self.setFixedHeight(min(300, self.height() + height))

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if (e.key() == Qt.Key.Key_Return or e.key() == Qt.Key.Key_Enter) and not self._shift_pressed:
            self.returnPressed.emit()
        elif e.key() == Qt.Key.Key_Shift:
            self._shift_pressed = True
            super().keyPressEvent(e)
        else:
            super().keyPressEvent(e)

    def keyReleaseEvent(self, e) -> None:
        if e.key() == Qt.Key.Key_Shift:
            self._shift_pressed = False
        super().keyPressEvent(e)


class _ScrollWidget(QWidget):
    resized = pyqtSignal()

    def resizeEvent(self, a0) -> None:
        super().resizeEvent(a0)
        self.resized.emit()


class MessageLoader(QThread):
    messageLoaded = pyqtSignal(GPTMessage)

    def __init__(self, chat):
        super().__init__()
        self._chat = chat

    def run(self) -> None:
        for el in reversed(self._chat.messages.values()):
            self.messageLoaded.emit(el)
            sleep(0.1)
