from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication
from PyQtUIkit.widgets import KitTextEdit


class ChatInputArea(KitTextEdit):
    returnPressed = pyqtSignal()
    resize = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setFixedHeight(26)
        self.textChanged.connect(self._on_text_changed)
        self.main_palette = 'Bg'
        self.border = 0
        self.max_height = 300

        self._shift_pressed = False

    def _on_text_changed(self):
        height = self.verticalScrollBar().maximum()
        if not height:
            self.setFixedHeight(26)
            height = self.verticalScrollBar().maximum()
        self.setFixedHeight(min(self.max_height, self.height() + height))

    def keyPressEvent(self, e: QKeyEvent) -> None:
        modifiers = QApplication.keyboardModifiers()
        if (e.key() == Qt.Key.Key_Return or e.key() == Qt.Key.Key_Enter) and \
                modifiers != Qt.KeyboardModifier.ShiftModifier:
            self.returnPressed.emit()
        else:
            super().keyPressEvent(e)
