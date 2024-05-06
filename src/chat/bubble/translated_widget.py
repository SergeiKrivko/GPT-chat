from PyQt6.QtCore import pyqtSignal, Qt
from PyQtUIkit.themes.locale import KitLocaleString
from PyQtUIkit.widgets import KitHBoxLayout, KitLabel, KitButton


class TranslatedWidget(KitHBoxLayout):
    showOriginal = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.setContentsMargins(8, 2, 2, 2)
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        self._label = KitLabel(KitLocaleString.translated_from)
        # self._label.font_size = FontSize.SMALL
        self.addWidget(self._label, 10)

        self._button = KitButton(KitLocaleString.show_original)
        # self._button.font_size = FontSize.SMALL
        self._button.clicked.connect(self.showOriginal.emit)
        self.addWidget(self._button)

    def set_src(self, src, service=''):
        self._label.text = getattr(KitLocaleString, f'translated_from_{src}')
