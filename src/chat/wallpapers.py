from PyQt6.QtGui import QPixmap, QPainter, QImage
from PyQtUIkit.widgets import KitHBoxLayout, KitVBoxLayout

from src import config


WIDTH = 1125
HEIGHT = 2436
SCALE = 5


def wallpapers(name, width, height, color):
    with open(f'{config.ASSETS_DIR}/wallpapers/{name}.svg', encoding='utf-8') as f:
        text = f.read()
    width *= SCALE
    height *= SCALE

    copies = []
    for x in range(0, width, WIDTH):
        for y in range(0, height, HEIGHT):
            if x or y:
                copies.append(f'<use href="#mainLayer" transform="translate({x}, {y})"/>')
    copies = '\n        '.join(copies) + '\n        '

    return eval(f'f"""{text}"""', {'width': width, 'height': height, 'scale': 5,
                                   'copies': copies, 'color': color})


class WallpaperWidget(KitVBoxLayout):
    def __init__(self):
        super().__init__()
        self._wallpaper = None
        self._pixmap = None
        self._painter = QPainter()

    def set_wallpaper(self, name):
        self._wallpaper = name
        self._update_pixmap()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_pixmap()

    def _update_pixmap(self):
        self._pixmap = None
        if self._tm is None or self._wallpaper is None:
            return
        svg = wallpapers(self._wallpaper, self.width(), self.height(), self._tm.palette('Chat').text).encode('utf-8')
        self._pixmap = QPixmap.fromImage(QImage.fromData(svg))

    def paintEvent(self, a0):
        super().paintEvent(a0)
        if not self._pixmap:
            return
        self._painter.begin(self)
        self._painter.drawPixmap(0, 0, self._pixmap)
        self._painter.end()

    def _apply_theme(self):
        super()._apply_theme()
        self._update_pixmap()

