from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QTextEdit

from src.gpt.chat import GPTChat
from src.ui.button import Button


class SearchWidget(QWidget):
    selectionRequested = pyqtSignal(int, int, int)

    def __init__(self, tm, chat: GPTChat):
        super().__init__()
        self._tm = tm
        self._chat = chat

        strange_layout = QVBoxLayout()
        strange_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(strange_layout)

        strange_widget = QWidget()
        strange_layout.addWidget(strange_widget)

        main_layout = QVBoxLayout()
        strange_widget.setLayout(main_layout)

        self._bubble = QWidget()
        main_layout.addWidget(self._bubble)

        strange_layout = QVBoxLayout()
        strange_layout.setContentsMargins(0, 0, 0, 0)
        self._bubble.setLayout(strange_layout)

        strange_widget = QWidget()
        strange_layout.addWidget(strange_widget)

        layout = QHBoxLayout()
        layout.setContentsMargins(8, 3, 3, 3)
        strange_widget.setLayout(layout)

        self._line_edit = QLineEdit()
        self._line_edit.setPlaceholderText("Поиск...")
        self._line_edit.textEdited.connect(self._search)
        layout.addWidget(self._line_edit)

        self._label = QLabel()
        layout.addWidget(self._label)

        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(0)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(buttons_layout)

        self._button_up = Button(self._tm, "up_arrow", css='Bg')
        self._button_up.clicked.connect(self._select_previous)
        buttons_layout.addWidget(self._button_up)

        self._button_down = Button(self._tm, "down_arrow", css='Bg')
        self._button_down.clicked.connect(self._select_next)
        buttons_layout.addWidget(self._button_down)

        self._current_selected = None
        self._search_result = []
        self._text_edit = QTextEdit()

    def _search(self):
        self._search_result.clear()
        substr = self._line_edit.text()

        if not substr.strip():
            return
        substr = substr.lower()
        for message in self._chat.messages:
            text: str = message.content.lower()
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
        self.selectionRequested.emit(*self._search_result[self._current_selected], len(self._line_edit.text()))

    def set_theme(self):
        self.setStyleSheet(f"background-color: {self._tm['MainColor']}")
        self._bubble.setStyleSheet(self._tm.base_css(palette='Bg', border=False, border_radius='8'))
        self._line_edit.setStyleSheet(self._tm.base_css(palette='Bg', border=False))
        self._line_edit.setFont(self._tm.font_medium)
        for el in [self._label, self._button_up, self._button_down]:
            self._tm.auto_css(el)
