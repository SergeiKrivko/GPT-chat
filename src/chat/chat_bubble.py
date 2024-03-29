from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFontMetrics, QIcon, QTextCursor, QFont
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QTextEdit, QMenu, QVBoxLayout, QSizePolicy, QLabel, QPushButton
from PyQtUIkit.widgets import *
from googletrans import LANGUAGES
from qasync import asyncSlot

from src.chat.render_latex import render_latex, delete_image
from src.chat.reply_widget import ReplyList
from src.gpt.message import GPTMessage
from src.gpt.translate import async_translate, async_detect


class ChatBubble(KitHBoxLayout):
    SIDE_LEFT = 0
    SIDE_RIGHT = 1

    _BORDER_RADIUS = 10

    deleteRequested = pyqtSignal()
    replyRequested = pyqtSignal()
    scrollRequested = pyqtSignal(int)
    textSelectionChanged = pyqtSignal()

    def __init__(self, sm, chat, message: GPTMessage):
        super().__init__()
        self._sm = sm
        self._chat = chat
        self._message = message
        self._side = ChatBubble.SIDE_RIGHT if message.role == 'user' else ChatBubble.SIDE_LEFT
        self._images = dict()

        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight if self._side == ChatBubble.SIDE_LEFT
                                else Qt.LayoutDirection.RightToLeft)
        self.setAlignment(Qt.AlignmentFlag.AlignTop |
                          Qt.AlignmentFlag.AlignLeft if self._side == ChatBubble.SIDE_LEFT else Qt.AlignmentFlag.AlignRight)
        self.setContentsMargins(0, 0, 0, 0)

        self._bubble_widget = KitVBoxLayout()
        self._bubble_widget.main_palette = 'UserMessage' if self._side == ChatBubble.SIDE_RIGHT else 'GptMessage'
        self._bubble_widget.radius = 10
        self._bubble_widget.border = 1
        self._bubble_widget.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed))
        self._bubble_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._bubble_widget.customContextMenuRequested.connect(
            lambda pos: self.run_context_menu(self._bubble_widget.mapToGlobal(pos)))
        self._bubble_widget.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._bubble_widget.setContentsMargins(4, 4, 4, 4)
        self.addWidget(self._bubble_widget, 10)

        self._reply_widget = ReplyList(self._chat, 2)
        self._reply_widget.scrollRequested.connect(self.scrollRequested.emit)
        self._reply_widget.hide()
        self._bubble_widget.addWidget(self._reply_widget)
        for el in self._message.replys:
            self._reply_widget.add_message(el)

        self._translated_widget = TranslatedWidget()
        self._translated_widget.hide()
        self._translated_widget.showOriginal.connect(self._show_original_message)
        self._bubble_widget.addWidget(self._translated_widget)

        self._font_metrics = QFontMetrics(QFont('Roboto', 11))

        self._text_edit = KitTextEdit()
        self._text_edit.main_palette = 'Transparent'
        self._text_edit.border = 0
        self._text_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._text_edit.customContextMenuRequested.connect(
            lambda pos: self.run_context_menu(self._text_edit.mapToGlobal(pos)))
        self._bubble_widget.setMaximumWidth(self._font_metrics.size(0, self._message.content).width() + 20)
        self._text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._text_edit.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse)
        self._text_edit.selectionChanged.connect(self._on_text_selection_changed)
        self._set_html()
        self._text_edit.setReadOnly(True)
        self._text_edit.textChanged.connect(self._resize)
        self._bubble_widget.addWidget(self._text_edit)

        self._widget = QWidget()
        self.addWidget(self._widget, 1)

    def _set_html(self):
        self._text_edit.setMarkdown(self.parse_latex())

    def parse_latex(self):
        lst = []

        text = self._message.content.replace('\\(', '\\[').replace('\\)', '\\]')
        while '\\[' in text:
            ind = text.index('\\[')
            lst.append(text[:ind])
            text = text[ind + 2:]

            if '\\]' in text:
                ind = text.index('\\]')
                formula = text[:ind]
                try:
                    if formula in self._images:
                        image = self._images[formula]
                    else:
                        image = render_latex(self._sm, self._tm, formula)
                        self._images[formula] = image
                    lst.append(f"![image.svg]({image})")
                except Exception:
                    lst.append(f"\\[ {formula} \\]")
                text = text[ind + 2:]

        lst.append(text)

        return ''.join(lst)

    def delete(self):
        for el in self._images:
            delete_image(el)

    def run_context_menu(self, pos):
        menu = ContextMenu(self, self)
        menu.move(pos)
        menu.exec()
        match menu.action:
            case ContextMenu.DELETE_MESSAGE:
                self.deleteRequested.emit()
            case ContextMenu.REPLY:
                self.replyRequested.emit()
            case ContextMenu.COPY_AS_TEXT:
                self._sm.copy_text(self._text_edit.toPlainText())
            case ContextMenu.COPY_AS_MARKDOWN:
                self._sm.copy_text(self._text_edit.toMarkdown())
            case ContextMenu.SELECT_ALL:
                self._text_edit.selectAll()
                self._text_edit.setFocus()
            case ContextMenu.TRANSLATE:
                self._translate_message(menu.data)
            case ContextMenu.SHOW_ORIGINAL:
                self._show_original_message()

    @asyncSlot()
    async def _translate_message(self, dest='ru'):
        res = await async_translate(self._text_edit.toMarkdown(), dest)
        self._translated_widget.set_src(res.src)
        self._translated_widget.show()
        self._text_edit.setMarkdown(res.text)

    def _show_original_message(self):
        self._translated_widget.hide()
        self._text_edit.setMarkdown(self.message.content)

    def resizeEvent(self, a0) -> None:
        super().resizeEvent(a0)
        self._resize()

    def showEvent(self, a0) -> None:
        super().showEvent(a0)
        self._resize()

    def _resize(self):
        self._text_edit.setFixedHeight(10)
        self._text_edit.setFixedHeight(10 + self._text_edit.verticalScrollBar().maximum())
        self._widget.setFixedHeight(self._text_edit.height())

    def add_text(self, text: str):
        self._message.add_text(text)
        self._set_html()
        self._bubble_widget.setMaximumWidth(self._font_metrics.size(0, self._message.content).width() + 20)

    @property
    def text(self):
        return self._message.content

    @property
    def message(self):
        return self._message

    @property
    def translated(self):
        return not self._translated_widget.isHidden()

    def _on_text_selection_changed(self):
        if self._text_edit.textCursor().hasSelection():
            self.textSelectionChanged.emit()

    def deselect_text(self):
        cursor = self._text_edit.textCursor()
        if cursor.hasSelection():
            cursor.clearSelection()
            self._text_edit.setTextCursor(cursor)

    def select_text(self, offset, length):
        cursor = self._text_edit.textCursor()
        cursor.setPosition(offset)
        cursor.setPosition(offset + length, QTextCursor.MoveMode.KeepAnchor)
        self._text_edit.setTextCursor(cursor)

    def _apply_theme(self):
        super()._apply_theme()
        css = f"""color: {self._tm['UserMessage' if self._side == ChatBubble.SIDE_RIGHT else 'GptMessage'].text}; 
            background-color: {self._tm['UserMessage' if self._side == ChatBubble.SIDE_RIGHT else 'GptMessage'].main};
            border: 1px solid {self._tm['Border'].main};
            border-top-left-radius: {ChatBubble._BORDER_RADIUS}px;
            border-top-right-radius: {ChatBubble._BORDER_RADIUS}px;
            border-bottom-left-radius: {0 if self._side == ChatBubble.SIDE_LEFT else ChatBubble._BORDER_RADIUS}px;
            border-bottom-right-radius: {0 if self._side == ChatBubble.SIDE_RIGHT else ChatBubble._BORDER_RADIUS}px;"""
        self._bubble_widget.setStyleSheet(css)
        self._widget.setStyleSheet("background-color: transparent; border: none;")
        self._set_html()


class ContextMenu(KitMenu):
    DELETE_MESSAGE = 1
    COPY_AS_TEXT = 2
    SELECT_ALL = 3
    SEND_TO_TELEGRAM = 4
    COPY_AS_MARKDOWN = 5
    REPLY = 6
    TRANSLATE = 7
    SHOW_ORIGINAL = 8

    def __init__(self, parent, bubble: ChatBubble):
        super().__init__(parent)
        self.action = None
        self.data = None

        action = self.addAction('Ответить', 'solid-reply')
        action.triggered.connect(lambda: self.set_action(ContextMenu.REPLY))

        self.addSeparator()

        action = self.addAction('Выделить все')
        action.triggered.connect(lambda: self.set_action(ContextMenu.SELECT_ALL))

        action = self.addAction('Копировать как текст', 'solid-copy')
        action.triggered.connect(lambda: self.set_action(ContextMenu.COPY_AS_TEXT))

        action = self.addAction('Копировать как Markdown', 'brands-markdown')
        action.triggered.connect(lambda: self.set_action(ContextMenu.COPY_AS_MARKDOWN))

        self.addSeparator()

        action = self.addAction('Удалить', 'solid-trash')
        action.triggered.connect(lambda: self.set_action(ContextMenu.DELETE_MESSAGE))

        self.addSeparator()

        if bubble.translated:
            action = self.addAction('Показать оригинал')
            action.triggered.connect(lambda: self.set_action(ContextMenu.SHOW_ORIGINAL))

        menu = self.addMenu('Перевести на ...', 'solid-language')
        for key, item in LANGUAGES.items():
            action = menu.addAction(item)
            action.triggered.connect(lambda x, lang=key: self.set_action(ContextMenu.TRANSLATE, lang))

        self.detect_lang(bubble.message.content)

    @asyncSlot()
    async def detect_lang(self, text):
        try:
            message_lang = await async_detect(text)
            message_lang = message_lang.lang
        except Exception:
            message_lang = None

        if message_lang != 'ru':
            action = self.addAction('Перевести на русский', 'solid-language')
            action.triggered.connect(lambda: self.set_action(ContextMenu.TRANSLATE, 'ru'))
            self._apply_theme()

    def set_action(self, action, data=None):
        self.action = action
        self.data = data


class _FakeMessage:
    def __init__(self):
        self._content = ''

    @property
    def content(self):
        return self._content

    def add_text(self, text):
        self._content += text

    @property
    def replys(self):
        return []

    @property
    def role(self):
        return 'assistant'

    @property
    def id(self):
        return -1


class FakeBubble(ChatBubble):
    def __init__(self, sm, chat):
        super().__init__(sm, chat, _FakeMessage())

    def set_theme(self):
        super().set_theme()


class TranslatedWidget(KitHBoxLayout):
    showOriginal = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.setContentsMargins(8, 2, 2, 2)
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        self._label = KitLabel("Переведено с _")
        # self._label.font_size = 'small'
        self.addWidget(self._label, 10)

        self._button = KitButton("Показать оригинал")
        # self._button.font_size = 'small'
        self._button.clicked.connect(self.showOriginal.emit)
        self.addWidget(self._button)

    def set_src(self, src):
        self._label.setText(f"Переведено с {LANGUAGES[src]}")

