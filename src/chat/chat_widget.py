from time import sleep

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication
from PyQtUIkit.widgets import KitVBoxLayout, KitHBoxLayout, KitIconButton, KitScrollArea, KitLabel, KitTextEdit, KitMenu
from googletrans import LANGUAGES

from src.chat.chat_bubble import ChatBubble, FakeBubble
from src.chat.reply_widget import ReplyList
from src.chat.search_widget import SearchWidget
from src.chat.settings_window import ChatSettingsWindow
from src.database import ChatManager
from src.gpt import gpt
from src.gpt.chat import GPTChat
from src.gpt.message import GPTMessage
from src.gpt.translate import translate, detect
from src.ui.message_box import MessageBox


class ChatWidget(KitVBoxLayout):
    buttonBackPressed = pyqtSignal(int)
    updated = pyqtSignal()

    def __init__(self, sm, tm, cm: ChatManager, um, chat: GPTChat):
        super().__init__()
        self._sm = sm
        self.tm = tm
        self._cm = cm
        self._um = um
        self._chat = chat

        self._bubbles = dict()

        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(0)

        self._top_layout = KitHBoxLayout()
        self._top_layout.main_palette = 'Bg'
        self._top_layout.radius = 0
        self._top_layout.setContentsMargins(8, 8, 8, 8)
        self._top_layout.setSpacing(5)
        self.addWidget(self._top_layout)

        self._button_back = KitIconButton('solid-arrow-left')
        self._button_back.size = 36
        self._button_back.main_palette = 'Bg'
        self._button_back.border = 0
        self._button_back.setContentsMargins(3, 3, 3, 3)
        self._button_back.clicked.connect(lambda: self.buttonBackPressed.emit(self._chat.id))
        self._top_layout.addWidget(self._button_back)

        self._name_label = KitLabel(chat.name if chat.name and chat.name.strip() else 'Диалог')
        self._top_layout.addWidget(self._name_label)

        self._button_search = KitIconButton('solid-magnifying-glass')
        self._button_search.size = 36
        self._button_search.main_palette = 'Bg'
        self._button_search.border = 0
        self._button_search.setContentsMargins(3, 3, 3, 3)
        self._button_search.clicked.connect(self._show_search)
        self._button_search.setCheckable(True)
        self._top_layout.addWidget(self._button_search)

        self._button_settings = KitIconButton('solid-gear')
        self._button_settings.size = 36
        self._button_settings.main_palette = 'Bg'
        self._button_settings.border = 0
        self._button_settings.setContentsMargins(3, 3, 3, 3)
        self._button_settings.clicked.connect(self._open_settings)
        self._top_layout.addWidget(self._button_settings)

        self._search_widget = SearchWidget(self.tm, self._chat)
        self._search_widget.selectionRequested.connect(self._select_text)
        self._search_widget.hide()
        self.addWidget(self._search_widget)

        self._scroll_area = ScrollArea()
        self._scroll_area.radius = 0
        self.addWidget(self._scroll_area, 1)
        self._scroll_area.verticalScrollBar().valueChanged.connect(self._on_scrolled)

        scroll_layout = _ScrollWidget()
        scroll_layout.radius = 0
        scroll_layout.resized.connect(self._scroll)
        self._scroll_area.setWidget(scroll_layout)
        scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._scroll_layout = KitVBoxLayout()
        self._scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.addWidget(self._scroll_layout)

        self._progress_marker = KitLabel("GPT печатает...")
        scroll_layout.addWidget(self._progress_marker)
        self._progress_marker.hide()

        text_bg_layout = KitVBoxLayout()
        text_bg_layout.main_palette = 'Main'
        text_bg_layout.radius = 0
        text_bg_layout.setContentsMargins(5, 5, 5, 5)
        self.addWidget(text_bg_layout)

        self._text_bubble = KitVBoxLayout()
        self._text_bubble.main_palette = 'Bg'
        self._text_bubble.radius = 8
        self._text_bubble.setContentsMargins(5, 5, 5, 5)
        text_bg_layout.addWidget(self._text_bubble)

        self._reply_list = ReplyList(self.tm, self._chat)
        self._reply_list.hide()
        self._reply_list.scrollRequested.connect(self.scroll_to_message)
        self._text_bubble.addWidget(self._reply_list)

        bottom_layout = KitHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        self._text_bubble.addWidget(bottom_layout)

        self._text_edit = ChatInputArea()
        self._text_edit.setPlaceholderText("Сообщение...")
        self._text_edit.returnPressed.connect(lambda: self.send_message())
        bottom_layout.addWidget(self._text_edit, 1)

        self._button = KitIconButton("solid-paper-plane")
        self._button.main_palette = 'Bg'
        self._button.size = 30
        self._button.border = 0
        self._button.radius = 5
        self._button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._button.customContextMenuRequested.connect(self._run_context_menu)
        self._button.clicked.connect(lambda: self.send_message())
        bottom_layout.addWidget(self._button)

        self._button_scroll = KitIconButton('solid-chevron-down')
        self._button_scroll.size = 36
        self._button_scroll.main_palette = 'Bg'
        self._button_scroll.setContentsMargins(7, 7, 7, 7)
        self._button_scroll.radius = self._button_scroll.size // 2
        self._scroll_area.resized.connect(
            lambda: self._button_scroll.move(self._scroll_area.width() - 51, self._scroll_area.height() - 46))
        self._button_scroll.clicked.connect(lambda: self._scroll(True, True))
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
        bubble = ChatBubble(self._sm, self._chat, message)
        self._add_bubble(bubble)
        return bubble

    def insert_bubble(self, message: GPTMessage):
        if message.id in self._bubbles:
            return
        bubble = ChatBubble(self._sm, self._chat, message)
        self._add_bubble(bubble, 0)
        return bubble

    def set_top_hidden(self, hidden):
        for el in [self._name_label, self._button_settings, self._button_back, self._top_layout]:
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
            self._last_bubble = FakeBubble(self._sm, self.tm, self._chat)
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
        menu = _SendMessageContextMenu(self, self._text_edit.toMarkdown())
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
        self._scroll_area.scrollTo(y=self._bubbles[message_id].pos().y() - 5, animation=True)

    def _on_scrolled(self):
        self._to_bottom = abs(self._scroll_area.verticalScrollBar().maximum() -
                              self._scroll_area.verticalScrollBar().value()) < 20
        self._button_scroll.setHidden(abs(self._scroll_area.verticalScrollBar().maximum() -
                                          self._scroll_area.verticalScrollBar().value()) < 300)
        self._chat.scrolling_pos = self._scroll_area.verticalScrollBar().value()
        if self._scroll_area.verticalScrollBar().value() <= 100 and not self._loading_messages:
            self._load_messages()

    def _scroll(self, to_bottom=False, anim=False):
        self._button_scroll.setHidden(self._to_bottom)
        if to_bottom or self._to_bottom:
            self._to_bottom = True
            self._scroll_area.scrollTo(y=self._scroll_area.verticalScrollBar().maximum(), animation=anim)
            if self._scroll_area.verticalScrollBar().value() < self._scroll_area.verticalScrollBar().maximum():
                self._scroll_area.scrollTo(y=self._scroll_area.verticalScrollBar().maximum(), animation=anim)
            self._button_scroll.setHidden(True)
        elif self._loading_messages:
            self._scroll_area.scrollTo(y=self._scroll_area.verticalScrollBar().value() +
                                         self._scroll_area.verticalScrollBar().maximum() - self._last_maximum,
                                       animation=anim)
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
        dialog = ChatSettingsWindow(self, self._sm, self._cm, self._um, self._chat)
        dialog.exec()
        dialog.save()
        self._name_label.setText(self._chat.name if self._chat.name.strip() else 'Диалог')
        self._chat._db.commit()

    def _on_gpt_error(self, ex):
        MessageBox(MessageBox.Icon.Warning, "Ошибка", f"{ex.__class__.__name__}: {ex}", self.tm)

    def _set_tm(self, tm):
        super()._set_tm(tm)
        self._button_scroll._set_tm(tm)

    def _apply_theme(self):
        super()._apply_theme()
        self._button_scroll._apply_theme()


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


class ChatInputArea(KitTextEdit):
    returnPressed = pyqtSignal()
    resize = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setFixedHeight(26)
        self.textChanged.connect(self._on_text_changed)
        self.main_palette = 'Bg'
        self.border = 0

        self._shift_pressed = False

    def _on_text_changed(self):
        height = self.verticalScrollBar().maximum()
        if not height:
            self.setFixedHeight(26)
            height = self.verticalScrollBar().maximum()
        self.setFixedHeight(min(300, self.height() + height))

    def keyPressEvent(self, e: QKeyEvent) -> None:
        modifiers = QApplication.keyboardModifiers()
        if (e.key() == Qt.Key.Key_Return or e.key() == Qt.Key.Key_Enter) and \
                modifiers != Qt.KeyboardModifier.ShiftModifier:
            self.returnPressed.emit()
        else:
            super().keyPressEvent(e)


class _ScrollWidget(KitVBoxLayout):
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


class ScrollArea(KitScrollArea):
    resized = pyqtSignal()

    def resizeEvent(self, a0) -> None:
        super().resizeEvent(a0)
        self.resized.emit()


class _SendMessageContextMenu(KitMenu):
    SEND = 1
    SEND_WITHOUT_REQUEST = 2
    TRANSLATE = 3

    def __init__(self, parent, text=''):
        super().__init__(parent)
        self.action = None
        self.data = None
        self.__height = 56
        try:
            message_lang = detect(text).lang
        except Exception:
            message_lang = None

        action = self.addAction('Отправить', 'solid-paper-plane')
        action.triggered.connect(lambda: self.set_action(_SendMessageContextMenu.SEND))

        action = self.addAction('Отправить без запроса', 'regular-paper-plane')
        action.triggered.connect(lambda: self.set_action(_SendMessageContextMenu.SEND_WITHOUT_REQUEST))

        self.addSeparator()

        if message_lang:
            self.__height += 33

            if message_lang != 'ru':
                self.__height += 24
                action = self.addAction('Перевести на русский', 'solid-language')
                action.triggered.connect(lambda: self.set_action(_SendMessageContextMenu.TRANSLATE, 'ru'))

            if message_lang != 'en':
                self.__height += 24
                action = self.addAction('Перевести на английский', 'solid-language')
                action.triggered.connect(lambda: self.set_action(_SendMessageContextMenu.TRANSLATE, 'en'))

            menu = self.addMenu('Перевести на ...', 'solid-language')
            for key, item in LANGUAGES.items():
                action = menu.addAction(item)
                action.triggered.connect(lambda x, lang=key: self.set_action(_SendMessageContextMenu.TRANSLATE, lang))

    def get_height(self):
        return self.__height

    def set_action(self, action, data=None):
        self.action = action
        self.data = data
