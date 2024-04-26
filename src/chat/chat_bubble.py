from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFontMetrics, QTextCursor, QFont
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQtUIkit.themes.locale import KitLocaleString
from PyQtUIkit.widgets import *
from qasync import asyncSlot
from translatepy import Language

from src.chat.render_latex import render_latex, delete_image
from src.chat.reply_widget import ReplyList
from src.gpt.message import GPTMessage
from src.gpt.translate import detect, LANGUAGES, translate_html
from src.settings_manager import SettingsManager


class ChatBubble(KitHBoxLayout):
    SIDE_LEFT = 0
    SIDE_RIGHT = 1

    _BORDER_RADIUS = 10

    deleteRequested = pyqtSignal()
    replyRequested = pyqtSignal()
    scrollRequested = pyqtSignal(int)
    textSelectionChanged = pyqtSignal()

    def __init__(self, sm: SettingsManager, chat, message: GPTMessage):
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
        self.setContentsMargins(10, 3, 10, 3)

        self._bubble_widget = KitVBoxLayout()
        self._bubble_widget.main_palette = 'UserMessage' if self._side == ChatBubble.SIDE_RIGHT else 'GptMessage'
        self._bubble_widget.radius = 10
        self._bubble_widget.border = 0
        self._bubble_widget.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed))
        self._bubble_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._bubble_widget.customContextMenuRequested.connect(
            lambda pos: self.run_context_menu(self._bubble_widget.mapToGlobal(pos)))
        self._bubble_widget.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._bubble_widget.setContentsMargins(4, 4, 4, 4)
        self.addWidget(self._bubble_widget, 10)

        self._font_metrics = QFontMetrics(QFont('Roboto', 11))
        width = self._font_metrics.size(0, self._message.content).width() + 20
        if len(list(self.message.replys)):
            width = max(width, 250)
        self._bubble_widget.setMaximumWidth(width)

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

        self._text_edit = KitTextEdit()
        self._text_edit.main_palette = 'Transparent'
        self._text_edit.border = 0
        self._text_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._text_edit.customContextMenuRequested.connect(
            lambda pos: self.run_context_menu(self._text_edit.mapToGlobal(pos)))
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

    def _set_html(self, text=None):
        self._text_edit.setMarkdown(self.parse_latex(text or self._message.content))
        html = self._text_edit.toHtml().replace("font-family:'Courier New'", "font-family:'Roboto Mono'").replace(
            "font-family:'Segoe UI'", "font-family:'Roboto'").replace('font-size:9pt', 'font-size:11pt')
        self._text_edit.setHtml(html)

    def parse_latex(self, text: str):
        lst = []

        text = text.replace('\\(', '\\[').replace('\\)', '\\]')
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
        menu = ContextMenu(self, self._sm)
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
                self._sm.copy_text(self._message.content)
            case ContextMenu.SELECT_ALL:
                self._text_edit.selectAll()
                self._text_edit.setFocus()
            case ContextMenu.TRANSLATE:
                self._translate_message(menu.data)
            case ContextMenu.SHOW_ORIGINAL:
                self._show_original_message()

    @asyncSlot()
    async def _translate_message(self, dest='ru'):
        res = await self._sm.run_async(lambda: translate_html(self._text_edit.toHtml(), dest),
                                       f'translate-{self._chat.id}')
        source = await self._sm.run_async(lambda: detect(self._text_edit.toMarkdown()), f'detect-{self._chat.id}')
        self._translated_widget.set_src(source.result.alpha2)
        self._translated_widget.show()
        self._text_edit.setHtml(res)

    def _show_original_message(self):
        self._translated_widget.hide()
        self._set_html()

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
    def plain_text(self):
        return self._text_edit.toPlainText()

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

    @property
    def selected_text(self):
        return self._text_edit.textCursor().selectedText()

    def _apply_theme(self):
        super()._apply_theme()
        # palette = 'UserMessage' if self._side == ChatBubble.SIDE_RIGHT else 'GptMessage'
        # css = f"""color: {self._tm.palette(palette).text};
        #     background-color: {self._tm.palette(palette).main};
        #     border: 1px solid {self.border_palette.main};
        #     border-top-left-radius: {ChatBubble._BORDER_RADIUS}px;
        #     border-top-right-radius: {ChatBubble._BORDER_RADIUS}px;
        #     border-bottom-left-radius: {0 if self._side == ChatBubble.SIDE_LEFT else ChatBubble._BORDER_RADIUS}px;
        #     border-bottom-right-radius: {0 if self._side == ChatBubble.SIDE_RIGHT else ChatBubble._BORDER_RADIUS}px;"""
        # self._bubble_widget.setStyleSheet(css)
        # self._widget.setStyleSheet("background-color: transparent; border: none;")
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

    def __init__(self, parent: ChatBubble, sm: SettingsManager):
        super().__init__(parent)
        self.action = None
        self.data = None
        self._sm = sm

        action = self.addAction(KitLocaleString.reply, 'custom-reply')
        action.triggered.connect(lambda: self.set_action(ContextMenu.REPLY))

        self.addSeparator()

        action = self.addAction(KitLocaleString.select_all, 'line-text')
        action.triggered.connect(lambda: self.set_action(ContextMenu.SELECT_ALL))

        action = self.addAction(KitLocaleString.copy_as_text, 'line-copy')
        action.triggered.connect(lambda: self.set_action(ContextMenu.COPY_AS_TEXT))

        action = self.addAction(KitLocaleString.copy_as_markdown, 'custom-copy-md')
        action.triggered.connect(lambda: self.set_action(ContextMenu.COPY_AS_MARKDOWN))

        self.addSeparator()

        action = self.addAction(KitLocaleString.delete, 'line-trash')
        action.triggered.connect(lambda: self.set_action(ContextMenu.DELETE_MESSAGE))

        self.addSeparator()

        if parent.translated:
            action = self.addAction(KitLocaleString.show_original)
            action.triggered.connect(lambda: self.set_action(ContextMenu.SHOW_ORIGINAL))

        menu = self.addMenu(KitLocaleString.translate_to, 'custom-translate')
        languages = [(key, getattr(KitLocaleString, f'lang_{key}').get(parent.theme_manager).capitalize())
                     for key in LANGUAGES]
        languages.sort(key=lambda x: x[1])
        for key, name in languages:
            action = menu.addAction(name)
            action.triggered.connect(lambda x, lang=key: self.set_action(ContextMenu.TRANSLATE, lang))

        self.detect_lang(parent.message.content)

    @asyncSlot()
    async def detect_lang(self, text):
        try:
            message_lang = await self._sm.run_async(lambda: detect(text), 'detect')
            message_lang = message_lang.result.alpha2
        except Exception:
            message_lang = None

        if message_lang != self.theme_manager.locale:
            action = self.addAction(KitLocaleString.translate_to_locale, 'custom-translate')
            action.triggered.connect(lambda: self.set_action(ContextMenu.TRANSLATE, self.theme_manager.locale))
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

    @content.setter
    def content(self, value):
        self._content = value

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


class TranslatedWidget(KitHBoxLayout):
    showOriginal = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.setContentsMargins(8, 2, 2, 2)
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        self._label = KitLabel(KitLocaleString.translated_from)
        # self._label.font_size = FontSize.SMALL
        self.addWidget(self._label, 10)

        self._button = KitButton(KitLocaleString.show_original)
        # self._button.font_size = FontSize.SMALL
        self._button.clicked.connect(self.showOriginal.emit)
        self.addWidget(self._button)

    def set_src(self, src, service=''):
        self._label.text = getattr(KitLocaleString, f'translated_from_{src}')
