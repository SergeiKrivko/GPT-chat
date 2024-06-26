from PyQt6.QtCore import pyqtSignal, QPropertyAnimation, QSize, QParallelAnimationGroup
from PyQt6.QtWidgets import QTextEdit
from PyQtUIkit.themes import KitPalette
from PyQtUIkit.themes.locale import KitLocaleString
from PyQtUIkit.widgets import KitVBoxLayout, KitVGroup, KitHBoxLayout, KitLineEdit, KitButton, KitLabel

from src.gpt.chat import GPTChat


class SearchWidget(KitVBoxLayout):
    selectionRequested = pyqtSignal(int, int, int)

    def __init__(self, chat: GPTChat):
        super().__init__()
        self._chat = chat

        self.setContentsMargins(5, 5, 5, 5)
        self.main_palette = 'Transparent'
        self.radius = 0

        self._bubble = KitHBoxLayout()
        self._bubble.main_palette = 'Bg'
        self._bubble.radius = 8
        self._bubble.setContentsMargins(8, 3, 3, 3)
        self._bubble.setSpacing(6)
        self.addWidget(self._bubble)

        self._line_edit = KitLineEdit()
        self._line_edit.border = 0
        self._line_edit.placeholder_text = KitLocaleString.search + "..."
        self._line_edit.textEdited.connect(self._search)
        self._bubble.addWidget(self._line_edit)

        self._label = KitLabel()
        self._bubble.addWidget(self._label)

        self._buttons_group = KitVGroup()
        self._buttons_group.width = 24
        self._buttons_group.main_palette = 'Bg'
        self._buttons_group.border = 0
        self._buttons_group.radius = 6
        self._bubble.addWidget(self._buttons_group)

        self._button_up = KitButton(icon='line-chevron-up')
        self._button_up.main_palette = 'Bg'
        self._button_up.clicked.connect(self._select_previous)
        self._buttons_group.addItem(self._button_up)

        self._button_down = KitButton(icon='line-chevron-down')
        self._button_down.main_palette = 'Bg'
        self._button_down.clicked.connect(self._select_next)
        self._buttons_group.addItem(self._button_down)

        self._current_selected = None
        self._search_result = []
        self.__anim = None
        self._text_edit = QTextEdit()

    def set_text(self, text: str):
        self._line_edit.setText(text)
        self._search()

    def _search(self):
        self._search_result.clear()
        substr = self._line_edit.text

        if not substr.strip():
            self._label.setText("")
            return
        substr = substr.lower()
        for message in self._chat.messages:
            text: str = self._clear_latex(message.content.lower())
            self._text_edit.setMarkdown(text)
            text = self._text_edit.toPlainText()

            offset = None
            try:
                while True:
                    offset = text.index(substr, 0 if offset is None else offset + len(substr))
                    self._search_result.append((message.id, offset))
            except ValueError:
                continue

        self._current_selected = len(self._search_result) - 1
        self._select_text()

    @staticmethod
    def _clear_latex(text: str):
        lst = []

        text = text.replace('\\(', '\\[').replace('\\)', '\\]')
        while '\\[' in text:
            ind = text.index('\\[')
            lst.append(text[:ind])
            text = text[ind + 2:]

            if '\\]' in text:
                ind = text.index('\\]')
                lst.append("⫘")
                text = text[ind + 2:]

        lst.append(text)

        return ''.join(lst)

    def set_focus(self):
        self._line_edit.setFocus()
        self._line_edit.selectAll()

    def _select_previous(self):
        if not self._search_result:
            return
        if self._current_selected is None:
            self._current_selected = 0
        elif self._current_selected == 0:
            self._current_selected = len(self._search_result) - 1
        else:
            self._current_selected -= 1
        self._select_text()

    def _select_next(self):
        if not self._search_result:
            return
        if self._current_selected is None:
            self._current_selected = 0
        else:
            self._current_selected = (self._current_selected + 1) % len(self._search_result)
        self._select_text()

    def _select_text(self):
        self._label.setText(f"{self._current_selected + 1}/{len(self._search_result)}")
        if self._search_result:
            self.selectionRequested.emit(*self._search_result[self._current_selected], len(self._line_edit.text))

    def _apply_theme(self):
        if not self._tm or not self._tm.active:
            return
        super()._apply_theme()
        self._line_edit.main_palette = KitPalette('#00000000', text=self.main_palette.text)
        self._button_up.setMinimumSize(24, 16)
        self._button_up.setContentsMargins(6, 6, 6, 6)
        self._button_down.setMinimumSize(24, 16)
        self._buttons_group.setFixedSize(24, 32)
