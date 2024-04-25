import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QFileDialog
from PyQtUIkit.themes.locale import KitLocaleString
from PyQtUIkit.widgets import *
from qasync import asyncSlot
from translatepy import Language

from src.chat.image_viewer import ImageViewer
from src.chat.input_area import ChatInputArea
from src.gpt.text_extract import extract_text
from src.settings_manager import SettingsManager


class ExtractTextDialog(KitDialog):
    IMAGE_MAX_WIDTH = 500
    IMAGE_MAX_HEIGHT = 500

    def __init__(self, parent, sm: SettingsManager):
        super().__init__(parent)
        self._sm = sm
        self.button_close = False
        self._file = ''
        self.resize(200, 200)

        main_layout = KitHBoxLayout()
        self.setWidget(main_layout)

        self._image_label = ImageViewer()
        self._image_label.setFixedSize(500, 500)
        self._image_label.main_palette = 'Bg'
        main_layout.addWidget(self._image_label)

        right_layout = KitVBoxLayout()
        right_layout.padding = 10
        right_layout.setFixedWidth(400)
        right_layout.spacing = 6
        main_layout.addWidget(right_layout)

        layout = KitHBoxLayout()
        layout.spacing = 6
        right_layout.addWidget(layout)
        layout.addWidget(KitLabel(KitLocaleString.language))

        self._language_box = KitComboBox()
        for lang in ['en', 'ru', 'de', 'fr', 'it', 'es', 'pt', 'zh', 'ja']:
            self._language_box.addItem(KitComboBoxItem(getattr(KitLocaleString, f'lang_{lang}'), lang))
        self._language_box.currentValueChanged.connect(lambda: self._extract_text())
        layout.addWidget(self._language_box)

        self._spinner = KitHBoxLayout()
        self._spinner.alignment = Qt.AlignmentFlag.AlignCenter
        right_layout.addWidget(self._spinner, 100)

        spinner = KitSpinner()
        spinner.size = 30
        spinner.width = 2
        self._spinner.addWidget(spinner)

        self._text_area = KitTextEdit()
        self._text_area.main_palette = 'Bg'
        self._text_area.border = 0
        self._text_area.hide()
        right_layout.addWidget(self._text_area)

        buttons_layout = KitHBoxLayout()
        buttons_layout.spacing = 6
        buttons_layout.alignment = Qt.AlignmentFlag.AlignRight
        right_layout.addWidget(buttons_layout)

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

    @property
    def path(self):
        return self._file

    def exec(self):
        file, _ = QFileDialog.getOpenFileName(filter="Images (*.png; *.jpg; *.jpeg; *.bmp)",
                                              directory=self._sm.get('last_file_directory'))
        if file:
            self._sm.set('last_file_directory', os.path.dirname(file))
            self._file = file
            self._apply_pixmap()
            return super().exec()
        return False

    def showEvent(self, a0) -> None:
        super().showEvent(a0)
        self._language_box.setCurrentValue(self._sm.get('extract_text_last_language', self.theme_manager.locale))

    def _apply_pixmap(self):
        pixmap = QPixmap(self._file)
        self._image_label.setPixmap(pixmap)
        # self._text_area.max_height = int(height) - 62
        self._image_label.setPixmap(pixmap)

    @asyncSlot()
    async def _extract_text(self):
        lang = Language(self._language_box.currentValue())
        self._sm.set('extract_text_last_language', lang.alpha2)

        self._text_area.hide()
        self._spinner.show()
        if self._file is None:
            return
        res = await extract_text(self._file, lang.alpha3)
        self._spinner.hide()
        self._text_area.show()
        self._text_area.setText(''.join(res))

    def accept(self):
        self._file = None
        super().accept()
