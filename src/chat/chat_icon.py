import json
import os.path
import shutil
from random import randint

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QPixmap, QImage, QBrush, QWindow
from PyQtUIkit.core import IconProperty, PaletteProperty
from PyQtUIkit.widgets import KitHBoxLayout, KitLabel

from src.gpt.chat import GPTChat
from src.settings_manager import SettingsManager


class ChatIcon(KitHBoxLayout):
    SIZE = 32

    def __init__(self, sm: SettingsManager, chat: GPTChat):
        super().__init__()
        self._sm = sm
        self._chat = chat
        self._icon = 'custom-icon-border'
        self.setFixedSize(ChatIcon.SIZE, ChatIcon.SIZE)

        self._circle = KitHBoxLayout()
        self._circle.setFixedSize(ChatIcon.SIZE, ChatIcon.SIZE)
        self._circle.radius = ChatIcon.SIZE // 2
        self.addWidget(self._circle)

        self._label = KitLabel()
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setFixedSize(ChatIcon.SIZE, ChatIcon.SIZE)
        self._circle.addWidget(self._label)

        self.__painter = QPainter()
        self._pixmap = QPixmap()

        self._load_icon()

    def import_image(self, path):
        self._clear_files()
        shutil.copy(path, os.path.join(self._sm.user_data_path, 'chat-icons', f'{self._chat.id}.png'))
        self._load_icon()
        self.draw()

    def clear_image(self):
        self._clear_files()
        self._load_icon()
        self._apply_theme()
        self.draw()

    def update_text(self):
        if self._pixmap:
            return
        path = os.path.join(self._sm.user_data_path, 'chat-icons', f'{self._chat.id}.json')
        self._generate_json(path, use_exists=True)
        self._load_data(path)
        self._apply_theme()

    def _clear_files(self):
        for ext in ['.png', '.json']:
            path = os.path.join(self._sm.user_data_path, 'chat-icons', f'{self._chat.id}{ext}')
            if os.path.isfile(path):
                os.remove(path)

    def _mask_image(self, image: QImage):

        # convert image to 32-bit ARGB (adds an alpha
        # channel ie transparency factor):
        image.convertToFormat(QImage.Format.Format_ARGB32)

        # Crop image to a square:
        imgsize = min(image.width(), image.height())
        rect = QRect(
            (image.width() - imgsize) // 2,
            (image.height() - imgsize) // 2,
            imgsize,
            imgsize,
        )

        image = image.copy(rect)

        # Create the output image with the same dimensions
        # and an alpha channel and make it completely transparent:
        out_img = QImage(imgsize, imgsize, QImage.Format.Format_ARGB32)
        out_img.fill(Qt.GlobalColor.transparent)

        # Create a texture brush and paint a circle
        # with the original image onto the output image:
        brush = QBrush(image)

        # Paint the output image
        painter = QPainter(out_img)
        painter.setBrush(brush)

        # Don't draw an outline
        painter.setPen(Qt.PenStyle.NoPen)

        # drawing circle
        painter.drawEllipse(0, 0, imgsize, imgsize)

        # closing painter event
        painter.end()

        # Convert the image to a pixmap and rescale it.
        pr = QWindow().devicePixelRatio()
        pm = QPixmap.fromImage(out_img)
        pm.setDevicePixelRatio(pr)
        size = int(self.SIZE * pr)
        pm = pm.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

        # return back the pixmap data
        return pm

    def _load_icon(self):
        path = os.path.join(self._sm.user_data_path, 'chat-icons', f'{self._chat.id}.png')
        # path = 'english.png'
        if not os.path.isfile(path):
            path = os.path.join(self._sm.user_data_path, 'chat-icons', f'{self._chat.id}.json')
            if not os.path.isfile(path):
                self._generate_json(path)
            self._pixmap = None
            self._load_data(path)
        else:
            self._pixmap = self._mask_image(QImage(path))

    def _generate_json(self, path, use_exists=False):
        os.makedirs(os.path.dirname(path), exist_ok=True)

        if use_exists and os.path.isfile(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = dict()

        with open(path, 'w', encoding='utf-8') as f:
            json.dump({
                'color': data.get('color', randint(0, 5)),
                'text': self._generate_text()
            }, f)

    def _generate_text(self):
        text = self._chat.name
        if len(text.split()) >= 2:
            text = text.split()[0][0] + text.split()[1][0]
        elif text != text.lower() and text != text.upper() and text != text.capitalize():
            for symbol in text[1:]:
                if symbol == symbol.upper():
                    text = text[0] + symbol
                    break
        elif len(text) > 1:
            text = text[:2]
        return text

    def _load_data(self, path):
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
            self._circle.main_palette = f"ChatIcon{data.get('color', 0)}"
            self._label.text = data.get('text', '')

    def paintEvent(self, a0) -> None:
        if self._tm and self._tm.active and self._pixmap:
            self.__painter.begin(self)

            self.__painter.drawPixmap(0, 0, self._pixmap.width(), self._pixmap.height(), self._pixmap)

            self.__painter.end()
        super().paintEvent(a0)

    def update_icon(self):
        self._load_icon()
        self._apply_theme()
        self.draw()

    def draw(self):
        if self._pixmap:
            self._circle.hide()
            self.update()
        else:
            self._circle.show()

    def _apply_theme(self):
        if not self._tm or not self._tm.active:
            return
        super()._apply_theme()
        self.draw()

