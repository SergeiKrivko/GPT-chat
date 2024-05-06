from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont, QFontMetrics, QTextCursor
from PyQt6.QtWidgets import QSizePolicy, QWidget
from PyQtUIkit.widgets import *
from qasync import asyncSlot

from src.chat.bubble.render_latex import delete_image
from src.chat.bubble.text_area import TextArea
from src.chat.bubble.translated_widget import TranslatedWidget
from src.chat.bubble.context_menu import ContextMenu
from src.chat.bubble.render_latex import render_latex
from src.chat.reply_widget import ReplyList
from src.gpt.message import GPTMessage
from src.gpt.translate import translate_html, detect
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

        self.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft if self._side == ChatBubble.SIDE_LEFT
                          else Qt.AlignmentFlag.AlignRight)
        self.setContentsMargins(10, 3, 10, 3)

        if self._side == ChatBubble.SIDE_RIGHT:
            self.addWidget(QWidget(), 1)

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

        self._text_area = TextArea(self._sm, self.parse_latex)
        self._text_area.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self._text_area.textSelected.connect(self.textSelectionChanged.emit)
        self._bubble_widget.addWidget(self._text_area)

        if self._side == ChatBubble.SIDE_LEFT:
            self.addWidget(QWidget(), 1)

        self._set_html()

    def _set_html(self, text=None):
        self._text_area.set_text(text or self._message.content)
        if self._text_area.has_code:
            self._bubble_widget.setMaximumWidth(10000)
        else:
            self._bubble_widget.setMaximumWidth(self._font_metrics.size(0, self._message.content).width() + 20)

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
                self._sm.copy_text(self._text_area.plain_text())
            case ContextMenu.COPY_AS_MARKDOWN:
                self._sm.copy_text(self._message.content)
            # case ContextMenu.SELECT_ALL:
            #     self._text_edit.selectAll()
            #     self._text_edit.setFocus()
            case ContextMenu.TRANSLATE:
                self._translate_message(menu.data)
            case ContextMenu.SHOW_ORIGINAL:
                self._show_original_message()

    @asyncSlot()
    async def _translate_message(self, dest='ru'):
        source = await self._text_area.translate(dest)
        self._translated_widget.set_src(source.result.alpha2)
        self._translated_widget.show()

    def _show_original_message(self):
        self._translated_widget.hide()
        self._text_area.show_original()

    def add_text(self, text: str):
        self._message.add_text(text)
        self._text_area.add_text(text)
        if self._text_area.has_code:
            self._bubble_widget.setMaximumWidth(10000)
        else:
            self._bubble_widget.setMaximumWidth(self._font_metrics.size(0, self._message.content).width() + 20)

    @property
    def text(self):
        return self._message.content

    @property
    def plain_text(self):
        return self._text_area.plain_text()

    @property
    def message(self):
        return self._message

    @property
    def translated(self):
        return not self._translated_widget.isHidden()

    def deselect_text(self):
        self._text_area.deselect_text()

    def select_text(self, offset, length):
        self._text_area.select(offset, length)

    @property
    def selected_text(self):
        return self._text_area.selected_text()
