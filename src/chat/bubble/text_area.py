from enum import Enum
from typing import Callable
from uuid import uuid4

from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QWidget, QHBoxLayout
from PyQtUIkit.widgets import KitVBoxLayout, KitTextBrowser, KitScintilla, KitHBoxLayout, KitLabel, KitHSeparator, \
    KitIconButton, KitApplication, KitTextEdit

from src.gpt.translate import translate_html, detect


class _Type(Enum):
    TEXT = 1
    CODE = 2


class _Part(QObject):
    textSelected = pyqtSignal(object)

    def __init__(self, tp: _Type, text: str, widget: QWidget | None):
        super().__init__()
        self.type = tp
        self.text = text
        self.widget = widget

    def add(self, text: str):
        self.text += text

    def resize(self):
        pass

    def plain_text(self):
        return self.text

    def deselect(self):
        pass


class _TextBrowser(KitTextEdit):
    def __init__(self):
        super().__init__()
        self.main_palette = 'Transparent'
        self.border = 0
        self.setReadOnly(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # self.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse)
        self.textChanged.connect(self.on_resize)

    def on_resize(self):
        self.setFixedHeight(10)
        self.setFixedHeight(10 + self.verticalScrollBar().maximum())


class _TextPart(_Part):
    def __init__(self, text: str, parse_latex: Callable):
        super().__init__(_Type.TEXT, text, None)
        self.widget = _TextBrowser()
        self.widget.selectionChanged.connect(self._on_selection_changed)
        self.__parse_latex = parse_latex
        self._apply_html()

    def add(self, text: str):
        super().add(text)
        self._apply_html()

    def _apply_html(self):
        self.widget.setMarkdown(self.__parse_latex(self.text))
        html = self.widget.toHtml().replace("font-family:'Courier New'", "font-family:'Roboto Mono'").replace(
            "font-family:'Segoe UI'", "font-family:'Roboto'").replace('font-size:9pt', 'font-size:11pt')
        self.widget.setHtml(html)

    def resize(self):
        self.widget.on_resize()

    def plain_text(self):
        return self.widget.toPlainText()

    def _on_selection_changed(self):
        if self.widget.textCursor().hasSelection():
            self.textSelected.emit(self)

    def deselect(self):
        cursor = self.widget.textCursor()
        if cursor.hasSelection():
            cursor.clearSelection()
            self.widget.setTextCursor(cursor)

    def selected_text(self):
        return self.widget.textCursor().selectedText()

    def select(self, offset: int, length: int):
        cursor = self.widget.textCursor()
        cursor.setPosition(offset)
        cursor.setPosition(offset + length, QTextCursor.MoveMode.KeepAnchor)
        self.widget.setTextCursor(cursor)


class _Scintilla(KitScintilla):
    def __init__(self):
        super().__init__()
        self.border = 0
        self.setReadOnly(True)
        self.setMargins(0)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_F:
            self.parent().keyPressEvent(e)


class _CodePart(_Part):
    def __init__(self, text: str):
        super().__init__(_Type.CODE, text, None)
        self.widget = KitVBoxLayout()
        self.widget.padding = 3
        self.widget.spacing = 3
        self.widget.main_palette = 'Main'

        top_layout = KitHBoxLayout()
        self.widget.addWidget(top_layout)

        self._lang_label = KitLabel()
        top_layout.addWidget(self._lang_label)

        button = KitIconButton('line-copy')
        button.setFixedSize(22, 22)
        button.on_click = self._copy
        top_layout.addWidget(button)

        self.widget.addWidget(KitHSeparator())

        self._scintilla = _Scintilla()
        self._scintilla.selectionChanged.connect(self._on_selection_changed)
        self.widget.addWidget(self._scintilla)

    def _copy(self):
        KitApplication.clipboard().setText(self._scintilla.text().replace('\r\n', '\n').replace('\r', '\n'))

    def add(self, text: str):
        super().add(text)
        lang = ''
        lines = self.text.splitlines()
        if lines and lines[0].startswith('```'):
            lang = lines[0].lstrip('`')
            lines.pop(0)
        if len(lines) >= 2 and lines[-1].startswith('```'):
            lines.pop()
        self._scintilla.setText('\n'.join(lines))
        self._scintilla.setFixedHeight(21 * len(lines))
        self._scintilla.language = lang
        self._lang_label.text = lang

    def plain_text(self):
        return self._scintilla.text()

    def _on_selection_changed(self):
        if self._scintilla.selectedText():
            self.textSelected.emit(self)

    def deselect(self):
        self._scintilla.setSelection(0, 0, 0, 0)

    def selected_text(self):
        return self._scintilla.selectedText()

    def select(self, offset: int, length: int):
        line_from = self.plain_text()[:offset].count('\n')
        index_from = len(self.plain_text()[:offset].split('\n')[-1])
        line_to = self.plain_text()[:offset + length].count('\n')
        index_to = len(self.plain_text()[:offset + length].split('\n')[-1])

        self._scintilla.setSelection(line_from, index_from, line_to, index_to)


class TextArea(KitVBoxLayout):
    textSelected = pyqtSignal()

    def __init__(self, sm, parse_latex: Callable):
        super().__init__()
        self._sm = sm
        self.__parts = []
        self.__parse_latex = parse_latex
        self._last_part = None

        self.__has_code = False

    def _add(self, part: _Part):
        self.__parts.append(part)
        if isinstance(part,_CodePart):
            self.__has_code = True
        part.textSelected.connect(self._on_text_selected)
        self.addWidget(part.widget)

    def clear(self):
        self.__has_code = False
        for el in self.__parts:
            el.disconnect()
        self.__parts.clear()
        super().clear()

    def set_text(self, text: str):
        self.clear()
        self._last_part = None
        for line in text.splitlines():
            self._new_line(line)

    def add_text(self, text):
        for line in text.splitlines():
            self._new_line(line)

    def _new_line(self, line):
        if line.startswith('```'):
            if isinstance(self._last_part, _CodePart):
                self._last_part.add(line + '\n')
                self._last_part = None
            else:
                self._last_part = _CodePart(line + '\n')
                self._add(self._last_part)
        elif self._last_part is None:
            self._last_part = _TextPart(line + '\n', self.__parse_latex)
            self._add(self._last_part)
        else:
            self._last_part.add(line + '\n')

    def plain_text(self):
        return '\n'.join(el.plain_text() for el in self.__parts)

    def _on_text_selected(self, selected_part):
        for part in self.__parts:
            if part != selected_part:
                part.deselect()
        self.textSelected.emit()

    def deselect_text(self):
        for part in self.__parts:
            part.deselect()

    def selected_text(self):
        for part in self.__parts:
            if text := part.selected_text():
                return text
        return None

    def select(self, offset: int, length: int):
        for part in self.__parts:
            part_len = len(part.plain_text())
            if part_len <= offset:
                offset -= part_len + 1
            else:
                part.select(offset, length)
                break

    @property
    def has_code(self):
        return self.__has_code

    async def translate(self, dest: str):
        source = None
        for part in self.__parts:
            if isinstance(part, _TextPart):
                if source is None:
                    source = await self._sm.run_async(lambda: detect(part.widget.toMarkdown()), f'detect-{uuid4()}')
                res = await self._sm.run_async(lambda: translate_html(part.widget.toHtml(), dest),
                                               f'translate-{uuid4()}')
                part.widget.setHtml(res)
        return source

    def show_original(self):
        for part in self.__parts:
            if isinstance(part, _TextPart):
                part._apply_html()

    def showEvent(self, a0):
        super().showEvent(a0)
        for part in self.__parts:
            part.resize()

    def resizeEvent(self, a0):
        super().resizeEvent(a0)
        for part in self.__parts:
            part.resize()

