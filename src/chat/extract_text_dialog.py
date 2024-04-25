from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QFileDialog
from PyQtUIkit.themes.locale import KitLocaleString
from PyQtUIkit.widgets import *
from qasync import asyncSlot

from src.chat.input_area import ChatInputArea
from src.gpt.text_extract import extract_text
from src.settings_manager import SettingsManager


class ExtractTextDialog(KitDialog):
    IMAGE_MAX_WIDTH = 300
    IMAGE_MAX_HEIGHT = 300

    def __init__(self, parent, sm: SettingsManager):
        super().__init__(parent)
        self._sm = sm
        self.button_close = False
        self._file = ''
        self.resize(400, 300)

        main_layout = KitVBoxLayout()
        main_layout.padding = 10
        main_layout.spacing = 10
        self.setWidget(main_layout)

        self._image_label = KitLabel(self)
        main_layout.addWidget(self._image_label)

        self._spinner = KitHBoxLayout()
        self._spinner.alignment = Qt.AlignmentFlag.AlignCenter
        main_layout.addWidget(self._spinner)

        spinner = KitSpinner()
        spinner.size = 30
        spinner.width = 2
        self._spinner.addWidget(spinner)

        self._text_area = ChatInputArea()
        self._text_area.hide()
        main_layout.addWidget(self._text_area)

        buttons_layout = KitHBoxLayout()
        buttons_layout.spacing = 6
        buttons_layout.alignment = Qt.AlignmentFlag.AlignRight
        main_layout.addWidget(buttons_layout)

        self._button_cancel = KitButton(KitLocaleString.cancel)
        self._button_cancel.setFixedSize(100, 26)
        self._button_cancel.on_click = self.reject
        buttons_layout.addWidget(self._button_cancel)

        self._button_send = KitButton(KitLocaleString.send)
        self._button_send.setFixedSize(100, 26)
        self._button_send.on_click = self.accept
        buttons_layout.addWidget(self._button_send)

    @property
    def text(self):
        return self._text_area.toPlainText()

    def exec(self):
        file, _ = QFileDialog.getOpenFileName(filter="Images (*.png; *.jpg; *.jpeg; *.bmp)")
        if file:
            self._file = file
            self._apply_pixmap()
            return super().exec()
        return False

    def showEvent(self, a0) -> None:
        super().showEvent(a0)
        self._extract_text()

    def _apply_pixmap(self):
        pixmap = QPixmap(self._file)
        width, height = pixmap.width(), pixmap.height()
        if pixmap.width() > ExtractTextDialog.IMAGE_MAX_WIDTH:
            height = height * ExtractTextDialog.IMAGE_MAX_WIDTH / width
            width = ExtractTextDialog.IMAGE_MAX_WIDTH
        if height > ExtractTextDialog.IMAGE_MAX_HEIGHT:
            width = width * ExtractTextDialog.IMAGE_MAX_HEIGHT / height
            height = ExtractTextDialog.IMAGE_MAX_HEIGHT
        pixmap = pixmap.scaled(int(width), int(height), Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
        self._image_label.setFixedSize(int(width), int(height))
        self._image_label.setPixmap(pixmap)

    @asyncSlot()
    async def _extract_text(self):
        res = await self._sm.run_async(lambda: extract_text(self._file), 'extract-text')
        self._spinner.hide()
        self._text_area.show()
        self._text_area.setText(''.join(res))
