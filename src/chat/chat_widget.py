from time import sleep

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint
from PyQt6.QtGui import QKeyEvent, QIcon
from PyQt6.QtWidgets import QVBoxLayout, QScrollArea, QWidget, QHBoxLayout, QTextEdit, QLabel, QApplication, QMenu
from googletrans import LANGUAGES

from src.chat.search_widget import SearchWidget
from src.database import ChatManager
from src.gpt import gpt
from src.chat.reply_widget import ReplyList
from src.gpt.chat import GPTChat
from src.chat.chat_bubble import ChatBubble, FakeBubble
from src.chat.settings_window import ChatSettingsWindow
from src.gpt.message import GPTMessage
from src.gpt.translate import translate, detect
from src.ui.button import Button
from src.ui.message_box import MessageBox


class ChatWidget(QWidget):
    buttonBackPressed = pyqtSignal(int)
    updated = pyqtSignal()

    def __init__(self, sm, tm, cm: ChatManager, chat: GPTChat):
        super().__init__()
        self._sm = sm
        self._tm = tm
        self._cm = cm
        self._chat = chat

        self._bubbles = dict()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        self._top_widget = QWidget()
        layout.addWidget(self._top_widget)

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(8, 8, 8, 8)
        top_layout.setSpacing(5)
        self._top_widget.setLayout(top_layout)

        self._button_back = Button(self._tm, 'button_back', css='Bg')
        self._button_back.setFixedSize(36, 36)
        self._button_back.clicked.connect(lambda: self.buttonBackPressed.emit(self._chat.id))
        top_layout.addWidget(self._button_back)

        self._name_label = QLabel(chat.name if chat.name and chat.name.strip() else 'Диалог')
        top_layout.addWidget(self._name_label)

        self._button_search = Button(self._tm, 'search', css='Bg')
        self._button_search.setFixedSize(36, 36)
        self._button_search.clicked.connect(self._show_search)
        self._button_search.setCheckable(True)
        top_layout.addWidget(self._button_search)

        self._button_settings = Button(self._tm, 'generate', css='Bg')
        self._button_settings.setFixedSize(36, 36)
        self._button_settings.clicked.connect(self._open_settings)
        top_layout.addWidget(self._button_settings)

        self._search_widget = SearchWidget(self._tm, self._chat)
        self._search_widget.selectionRequested.connect(self._select_text)
        self._search_widget.hide()
        layout.addWidget(self._search_widget)

        self._scroll_area = ScrollArea()
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

        self._text_bg = QWidget()
        layout.addWidget(self._text_bg)

        strange_layout = QVBoxLayout()
        strange_layout.setContentsMargins(0, 0, 0, 0)
        self._text_bg.setLayout(strange_layout)
        strange_widget = QWidget()
        strange_layout.addWidget(strange_widget)

        text_bg_layout = QHBoxLayout()
        strange_widget.setLayout(text_bg_layout)

        self._text_bubble = QWidget()
        text_bg_layout.addWidget(self._text_bubble)

        strange_layout = QVBoxLayout()
        strange_layout.setContentsMargins(0, 0, 0, 0)
        self._text_bubble.setLayout(strange_layout)
        strange_widget = QWidget()
        strange_layout.addWidget(strange_widget)

        bubble_layout = QVBoxLayout()
        bubble_layout.setContentsMargins(5, 5, 5, 5)
        strange_widget.setLayout(bubble_layout)

        self._reply_list = ReplyList(self._tm, self._chat)
        self._reply_list.hide()
        self._reply_list.scrollRequested.connect(self.scroll_to_message)
        bubble_layout.addWidget(self._reply_list)

        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bubble_layout.addLayout(bottom_layout)

        self._text_edit = ChatInputArea()
        self._text_edit.setPlaceholderText("Сообщение...")
        self._text_edit.returnPressed.connect(lambda: self.send_message())
        bottom_layout.addWidget(self._text_edit, 1)

        self._button = Button(self._tm, "button_send", css='Bg')
        self._button.setFixedSize(30, 30)
        self._button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._button.customContextMenuRequested.connect(self._run_context_menu)
        self._button.clicked.connect(lambda: self.send_message())
        bottom_layout.addWidget(self._button)

        self._button_scroll = Button(self._tm, 'down_arrow', css='Bg')
        self._button_scroll.setFixedSize(36, 36)
        self._scroll_area.resized.connect(
            lambda: self._button_scroll.move(self._scroll_area.width() - 51, self._scroll_area.height() - 46))
        self._button_scroll.clicked.connect(lambda: self._scroll(True))
        self._button_scroll.setParent(self._scroll_area)

        self.looper = None
        self._last_bubble = None
        self._last_message = None
        self._to_bottom = True
        self._last_maximum = 0
        self._want_to_scroll = None
        self._messages_is_loaded = False
        self._loading_messages = False
        self._sending_message = None
        self._bubble_with_selected_text = None

    def _load_messages(self, to_message=None):
        self._loading_messages = True
        self._messages_is_loaded = True
        loader = MessageLoader(list(self._chat.load_messages(to_message=to_message)))
        loader.messageLoaded.connect(self.insert_bubble)
        loader.finished.connect(self._on_load_finished)
        self._sm.run_process(loader, f"load-{self._chat.id}")

    def _on_load_finished(self):
        self._loading_messages = False
        if self._want_to_scroll is not None:
            self.scroll_to_message(self._want_to_scroll)
            self._want_to_scroll = None

    def send_message(self, run_gpt=True):
        if not ((text := self._text_edit.toPlainText()).strip()):
            return
        self._sending_message = text if run_gpt else ''
        self._cm.new_message(self._chat.id, 'user', text, tuple(self._reply_list.messages))
        self._text_edit.setText("")

    def add_message(self, message):
        if message.id in self._bubbles:
            return
        self.add_bubble(message)
        self.run_gpt(message)

    def delete_message(self, message_id):
        bubble = self._bubbles.pop(message_id)
        bubble.setParent(None)
        bubble.disconnect()
        bubble.delete()

    def run_gpt(self, message):
        if message.role != 'user' or message.content != self._sending_message:
            return
        if self._last_bubble:
            self._bubbles.pop(self._last_bubble.message.id)
            self._last_bubble.setParent(None)
            self._last_bubble = None
        self._sending_message = None

        messages = self._chat.messages_to_prompt(list(self._reply_list.messages))
        for el in self._reply_list.messages:
            self._chat.get_message(el).replied_count += 1
        self._reply_list.clear()

        self.looper = Looper(messages, self._chat, model=self._chat.model, temperature=self._chat.temperature)
        if isinstance(self.looper, Looper) and not self.looper.isFinished():
            self.looper.terminate()
        self._last_message = None
        self._progress_marker.show()
        self.looper.sendMessage.connect(self.add_text)
        self.looper.exception.connect(self._on_gpt_error)
        self.looper.finished.connect(self.finish_gpt)
        self.looper.start()

    def add_bubble(self, message: GPTMessage):
        if message.id in self._bubbles:
            return
        bubble = ChatBubble(self._sm, self._tm, self._chat, message)
        self._add_bubble(bubble)
        return bubble

    def insert_bubble(self, message: GPTMessage):
        if message.id in self._bubbles:
            return
        bubble = ChatBubble(self._sm, self._tm, self._chat, message)
        self._add_bubble(bubble, 0)
        return bubble

    def set_top_hidden(self, hidden):
        for el in [self._name_label, self._button_settings, self._button_back, self._top_widget]:
            el.setHidden(hidden)

    def _select_text(self, message_id, offset, length):
        if message_id in self._bubbles:
            self._bubbles[message_id].select_text(offset, length)
            self.scroll_to_message(message_id)

    def _on_text_selected(self, bubble):
        if self._bubble_with_selected_text == bubble:
            return
        if self._bubble_with_selected_text:
            self._bubble_with_selected_text.deselect_text()
        self._bubble_with_selected_text = bubble

    @property
    def search_active(self):
        return self._button_search.isChecked()

    def show_search(self, flag):
        self._button_search.setChecked(flag)
        self._show_search()

    def _show_search(self):
        self._search_widget.setHidden(not self.search_active)

    def _add_bubble(self, bubble, index=None):
        bubble.deleteRequested.connect(lambda: self._cm.delete_message(self._chat.id, bubble.message))
        bubble.replyRequested.connect(lambda: self._reply_list.add_message(bubble.message))
        bubble.scrollRequested.connect(self.scroll_to_message)
        bubble.textSelectionChanged.connect(lambda: self._on_text_selected(bubble))
        if index is None:
            self.updated.emit()
            self._scroll_layout.addWidget(bubble)
            self._bubbles[bubble.message.id] = bubble
        else:
            self._scroll_layout.insertWidget(index, bubble)
            self._bubbles[bubble.message.id] = bubble
        bubble.set_theme()

    def add_text(self, text):
        if self._last_bubble is None:
            self._last_bubble = FakeBubble(self._sm, self._tm, self._chat)
            self._add_bubble(self._last_bubble)
        self._last_bubble.add_text(text)

    def finish_gpt(self):
        if self._last_bubble:
            bubble = self._last_bubble
            self._last_bubble = None
            bubble.setParent(None)
            self._bubbles.pop(bubble.message.id)
            self._cm.new_message(self._chat.id, 'assistant', bubble.message.content)
        self._progress_marker.hide()

    def _run_context_menu(self, pos):
        if not self._text_edit.toMarkdown():
            return
        menu = _SendMessageContextMenu(self._tm, self._text_edit.toMarkdown())
        pos = self._button.mapToGlobal(pos)
        menu.move(pos - QPoint(206, menu.get_height()))
        menu.exec()
        match menu.action:
            case _SendMessageContextMenu.SEND:
                self.send_message()
            case _SendMessageContextMenu.SEND_WITHOUT_REQUEST:
                self.send_message(False)
            case _SendMessageContextMenu.TRANSLATE:
                self._text_edit.setText(translate(self._text_edit.toPlainText(), menu.data).text)

    def scroll_to_message(self, message_id):
        if message_id not in self._bubbles:
            if not self._chat.get_message(message_id).deleted:
                self._want_to_scroll = message_id
                self._load_messages(to_message=message_id)
            return
        self._scroll_area.verticalScrollBar().setValue(self._bubbles[message_id].pos().y() - 5)

    def _on_scrolled(self):
        self._to_bottom = abs(self._scroll_area.verticalScrollBar().maximum() -
                              self._scroll_area.verticalScrollBar().value()) < 20
        self._button_scroll.setHidden(abs(self._scroll_area.verticalScrollBar().maximum() -
                                          self._scroll_area.verticalScrollBar().value()) < 300)
        self._chat.scrolling_pos = self._scroll_area.verticalScrollBar().value()
        if self._scroll_area.verticalScrollBar().value() <= 100 and not self._loading_messages:
            self._load_messages()

    def _scroll(self, to_bottom=False):
        self._button_scroll.setHidden(self._to_bottom)
        if to_bottom or self._to_bottom:
            self._to_bottom = True
            self._scroll_area.verticalScrollBar().setValue(self._scroll_area.verticalScrollBar().maximum())
            if self._scroll_area.verticalScrollBar().value() < self._scroll_area.verticalScrollBar().maximum():
                self._scroll_area.verticalScrollBar().setValue(self._scroll_area.verticalScrollBar().maximum())
            self._button_scroll.setHidden(True)
        elif self._loading_messages:
            self._scroll_area.verticalScrollBar().setValue(self._scroll_area.verticalScrollBar().value() +
                                                           self._scroll_area.verticalScrollBar().maximum() -
                                                           self._last_maximum)
        self._last_maximum = self._scroll_area.verticalScrollBar().maximum()

    def showEvent(self, a0) -> None:
        super().showEvent(a0)
        if not self._messages_is_loaded:
            self._load_messages()
        # self._scroll_area.verticalScrollBar().setValue(self._chat.scrolling_pos)

    def hideEvent(self, a0) -> None:
        super().hideEvent(a0)
        lst = list(self._bubbles.keys())
        lst.sort(reverse=False)
        ind = 0
        for i, el in enumerate(lst):
            if self._bubbles[el].pos().y() < self._scroll_area.verticalScrollBar().value():
                ind = i
        ind -= 5
        if ind > 0:
            for el in self._chat.drop_messages(self._bubbles[lst[ind]].message.id):
                bubble: ChatBubble = self._bubbles.pop(el.id)
                bubble.setParent(None)
                bubble.delete()
                bubble.disconnect()

    def _open_settings(self):
        dialog = ChatSettingsWindow(self._sm, self._tm, self._cm, self._chat)
        dialog.exec()
        dialog.save()
        self._name_label.setText(self._chat.name if self._chat.name.strip() else 'Диалог')
        self._chat._db.commit()

    def _on_gpt_error(self, ex):
        MessageBox(MessageBox.Icon.Warning, "Ошибка", f"{ex.__class__.__name__}: {ex}", self._tm)

    def set_theme(self):
        self._tm.auto_css(self._text_edit, palette='Bg', border_radius='4', border=False)
        for el in [self._button, self._button_back, self._name_label, self._button_settings, self._button_scroll,
                   self._button_search]:
            self._tm.auto_css(el)
        self._search_widget.set_theme()
        self._scroll_widget.setStyleSheet(self._tm.base_css(palette='Main', border=False))
        self._text_bg.setStyleSheet(self._tm.base_css(palette='Main', border=False, border_radius=False))
        self._text_bubble.setStyleSheet(self._tm.base_css(palette='Bg', border=False, border_radius='8'))
        self._tm.auto_css(self._scroll_area, palette='Main', border_radius=False, border=False)

        css = f"""
        QPushButton {{
            background-color: {self._tm['BgColor']};  
            border: 1px solid {self._tm['BorderColor']}; 
            border-radius: {self._button_scroll.width() // 2}px; 
        }}
        QPushButton:hover {{
            background-color: {self._tm['BgHoverColor']};
        }}
        """
        self._button_scroll.setStyleSheet(css)
        self._progress_marker.setStyleSheet(f"background-color: {self._tm['MainColor']}")

        for el in self._bubbles.values():
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
            for el in gpt.stream_response(self.text, **self.kwargs):
                self.sendMessage.emit(el)
            sleep(0.1)
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
        modifiers = QApplication.keyboardModifiers()
        if (e.key() == Qt.Key.Key_Return or e.key() == Qt.Key.Key_Enter) and \
                modifiers != Qt.KeyboardModifier.ShiftModifier:
            self.returnPressed.emit()
        else:
            super().keyPressEvent(e)


class _ScrollWidget(QWidget):
    resized = pyqtSignal()

    def resizeEvent(self, a0) -> None:
        super().resizeEvent(a0)
        self.resized.emit()


class MessageLoader(QThread):
    messageLoaded = pyqtSignal(GPTMessage)

    def __init__(self, messages):
        super().__init__()
        self._messages = messages

    def run(self) -> None:
        for el in self._messages:
            self.messageLoaded.emit(el)
            sleep(0.1)


class ScrollArea(QScrollArea):
    resized = pyqtSignal()

    def resizeEvent(self, a0) -> None:
        super().resizeEvent(a0)
        self.resized.emit()


class _SendMessageContextMenu(QMenu):
    SEND = 1
    SEND_WITHOUT_REQUEST = 2
    TRANSLATE = 3

    def __init__(self, tm, text=''):
        super().__init__()
        self.action = None
        self.data = None
        self.__height = 56
        try:
            message_lang = detect(text).lang
        except Exception:
            message_lang = None

        action = self.addAction(QIcon(tm.get_image('button_send')), 'Отправить')
        action.triggered.connect(lambda: self.set_action(_SendMessageContextMenu.SEND))

        action = self.addAction(QIcon(tm.get_image('send2')), 'Отправить без запроса')
        action.triggered.connect(lambda: self.set_action(_SendMessageContextMenu.SEND_WITHOUT_REQUEST))

        self.addSeparator()

        if message_lang:
            self.__height += 33

            if message_lang != 'ru':
                self.__height += 24
                action = self.addAction(QIcon(tm.get_image('translate')), 'Перевести на русский')
                action.triggered.connect(lambda: self.set_action(_SendMessageContextMenu.TRANSLATE, 'ru'))

            if message_lang != 'en':
                self.__height += 24
                action = self.addAction(QIcon(tm.get_image('translate')), 'Перевести на английский')
                action.triggered.connect(lambda: self.set_action(_SendMessageContextMenu.TRANSLATE, 'en'))

            menu = self.addMenu(QIcon(tm.get_image('translate')), 'Перевести на ...')
            for key, item in LANGUAGES.items():
                action = menu.addAction(item)
                action.triggered.connect(lambda x, lang=key: self.set_action(_SendMessageContextMenu.TRANSLATE, lang))

        self.setStyleSheet(tm.menu_css(palette='Menu'))

    def get_height(self):
        return self.__height

    def set_action(self, action, data=None):
        print(self.height())
        self.action = action
        self.data = data
