from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

from src.ui.button import Button


class CustomDialog(QDialog):
    def __init__(self, tm, name='', button_close=False, panel=False):
        super().__init__()
        self.tm = tm
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.__panel = panel

        layout = QVBoxLayout()
        layout.setContentsMargins(1, 1, 1, 1)
        super().setLayout(layout)

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(10, 2, 2, 2)

        self.__top_widget = QWidget()
        self.__top_widget.setFixedHeight(32)
        layout.addWidget(self.__top_widget)
        self.__top_widget.setLayout(top_layout)

        self.__label = QLabel(name)
        self.__label.setFixedHeight(25)
        if name:
            top_layout.addWidget(self.__label)

        self.__button_close = Button(self.tm, 'button_close', css='Menu' if panel else 'Bg')
        self.__button_close.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.__button_close.setFixedSize(25, 25)
        if button_close:
            top_layout.addWidget(self.__button_close)
            self.__button_close.clicked.connect(self.reject)

        self.__widget = QWidget()
        layout.addWidget(self.__widget)

        self.__moving = False
        self.__last_pos = None

    def setLayout(self, a0) -> None:
        self.__widget.setLayout(a0)

    def mousePressEvent(self, a0) -> None:
        if a0.button() == Qt.MouseButton.LeftButton:
            self.__moving = True
            self.__last_pos = a0.pos()

    def mouseReleaseEvent(self, a0) -> None:
        if a0.button() == Qt.MouseButton.LeftButton:
            self.__moving = False
            self.__last_pos = None

    def mouseMoveEvent(self, a0) -> None:
        if self.__moving:
            self.move(self.pos() + a0.pos() - self.__last_pos)

    def set_theme(self):
        css = f"""
    color: {self.tm['TextColor']};
    background-color: {self.tm['BgColor']};
    border: 1px solid {self.tm['BorderColor']};
    border-radius: 5px;
        """
        self.setStyleSheet(css)
        self.__widget.setStyleSheet("border: none;")
        if self.__panel:
            self.__top_widget.setStyleSheet(
                f"background-color: {self.tm['MenuColor' if self.__panel else self.tm['BgColor']]};"
                f"border-left: 0px;"
                f"border-top: 0px;"
                f"border-right: 0px;"
                f"border-bottom: 1px solid {self.tm['BorderColor']};"
                f"border-bottom-left-radius: 0px;"
                f"border-bottom-right-radius: 0px;")
        else:
            self.__top_widget.setStyleSheet("border: none;")
        for el in [self.__label, self.__button_close]:
            self.tm.auto_css(el)


class _AskDialog(CustomDialog):
    def __init__(self, tm, question: str, answers=('Нет', 'Да'), default=''):
        super().__init__(tm)
        self._answers = answers

        self.setMinimumSize(250, 150)

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        self._label = QLabel(question)
        self._label.setWordWrap(True)
        main_layout.addWidget(self._label)

        buttons_layout = QHBoxLayout()
        buttons_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addLayout(buttons_layout)

        self._buttons = dict()
        self._answer = default

        for el in answers:
            button = QPushButton(el)
            buttons_layout.addWidget(button)
            button.clicked.connect(lambda f, a=el: self._on_button_clicked(a))
            self._buttons[el] = button

    def _on_button_clicked(self, answer):
        self._answer = answer
        self.accept()

    @property
    def answer(self):
        return self._answer

    def set_theme(self):
        super().set_theme()
        self.tm.auto_css(self._label)
        for el in self._buttons.values():
            self.tm.auto_css(el, padding=True)


def ask(tm, question: str, answers=('Нет', 'Да'), default=''):
    dialog = _AskDialog(tm, question, answers, default)
    dialog.set_theme()
    dialog.exec()
    return dialog.answer
