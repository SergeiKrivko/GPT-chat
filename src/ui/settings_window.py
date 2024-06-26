from PyQt6.QtCore import Qt, pyqtSignal
from PyQtUIkit.themes.locale import KitLocaleString
from PyQtUIkit.widgets import *

import src.gpt.translate as translate
from src.ui.patch_notes_dialog import PatchNotesDialog
from src.ui.plugins_window import PluginsWindow
from src.ui.update_manager import UpdateManager


class SettingsWindow(KitDialog):
    wallpaperChanged = pyqtSignal(int)

    def __init__(self, parent, sm, cm, um: UpdateManager):
        super().__init__(parent)
        self.sm = sm
        self._cm = cm
        self._um = um
        self.name = KitLocaleString.settings
        self.main_palette = 'Bg'

        self._labels = []
        self.setFixedWidth(400)

        main_layout = KitVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(8)
        self.setWidget(main_layout)

        lang_box = KitLanguageBox()
        lang_box.langChanged.connect(self._on_lang_changed)
        main_layout.addWidget(lang_box)

        self._theme_checkbox = KitCheckBox(KitLocaleString.dark_theme)
        self._theme_checkbox.main_palette = 'Bg'
        self._theme_checkbox.setChecked(self.sm.get('dark_theme', 'light') == 'dark')
        self._theme_checkbox.stateChanged.connect(self._on_theme_changed)
        main_layout.addWidget(self._theme_checkbox)

        layout = KitHBoxLayout()
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        main_layout.addWidget(layout)
        layout.addWidget(KitLabel(KitLocaleString.theme_color + ':'))

        self._theme_box = KitComboBox(KitComboBoxItem(KitLocaleString.blue, 'blue'),
                                      KitComboBoxItem(KitLocaleString.green, 'green'),
                                      KitComboBoxItem(KitLocaleString.red, 'red'),
                                      KitComboBoxItem(KitLocaleString.orange, 'orange'),
                                      KitComboBoxItem(KitLocaleString.pink, 'pink'), )
        self._theme_box.setCurrentIndex(['blue', 'green', 'red', 'orange', 'pink'].index(self.sm.get('theme', 'blue')))
        self._theme_box.currentValueChanged.connect(self._on_theme_changed)
        layout.addWidget(self._theme_box)

        layout = KitHBoxLayout()
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        main_layout.addWidget(layout)
        layout.addWidget(KitLabel(KitLocaleString.wallpaper + ':'))

        self._wallpaper_box = KitComboBox(KitComboBoxItem(KitLocaleString.no_wallpaper, 0))
        for i in range(1, 32):
            if i not in [3, 11]:
                self._wallpaper_box.addItem(KitComboBoxItem(getattr(KitLocaleString, f'wallpaper_{i}'), i))
        self._wallpaper_box.setCurrentValue(int(self.sm.get('wallpaper', 0)))
        self._wallpaper_box.currentValueChanged.connect(self._on_wallpaper_changed)
        layout.addWidget(self._wallpaper_box)

        main_layout.addWidget(KitHSeparator())

        self._update_widget = UpdateWidget()
        self._um.set_widget(self._update_widget)
        self._update_widget.clicked.connect(lambda: self._um.check_release(say_if_no_release=True))
        self._update_widget.cancel.connect(lambda: self._um.cancel_downloading())
        main_layout.addWidget(self._update_widget)

        self._auto_update_checkbox = KitCheckBox(KitLocaleString.report_updates)
        self._auto_update_checkbox.main_palette = 'Bg'
        self._auto_update_checkbox.setChecked(bool(self.sm.get('auto_update', True)))
        main_layout.addWidget(self._auto_update_checkbox)

        self._patch_notes_window = PatchNotesDialog(parent, self.sm)
        self._patch_notes_button = KitButton(KitLocaleString.patch_note)
        self._patch_notes_button.on_click = self._patch_notes_window.exec
        main_layout.addWidget(self._patch_notes_button)

        main_layout.addWidget(KitHSeparator())

        layout = KitHBoxLayout()
        layout.spacing = 6
        main_layout.addWidget(layout)
        layout.addWidget(KitLabel(KitLocaleString.translator + ':'))

        self._translator_box = KitComboBox()
        layout.addWidget(self._translator_box)
        self._translator_box.addItem(KitComboBoxItem(KitLocaleString.default, None))
        for el in translate.SERVICES:
            self._translator_box.addItem(el, el)
        self._translator_box.setCurrentValue(self.sm.get('translator'))
        self._translator_box.currentValueChanged.connect(self._on_translator_changed)

        self._plugins_button = KitButton(KitLocaleString.custom_providers)
        self._plugins_button.on_click = self._plugins_widow
        main_layout.addWidget(self._plugins_button)

    def _plugins_widow(self):
        dialog = PluginsWindow(self, self.sm, self._cm)
        dialog.exec()

    def save(self):
        self.sm.set('auto_update', 'true' if self._auto_update_checkbox.state else '')

    def _on_theme_changed(self):
        self.sm.set('dark_theme', 'dark' if self._theme_checkbox.state else 'light')
        self.sm.set('theme', self._theme_box.currentValue())
        self.theme_manager.set_theme(f"{self.sm.get('dark_theme')}_{self.sm.get('theme')}")
        self._apply_theme()

    def _on_wallpaper_changed(self):
        self.sm.set('wallpaper', self._wallpaper_box.currentValue())
        self.wallpaperChanged.emit(self._wallpaper_box.currentValue())

    def _on_translator_changed(self):
        self.sm.set('translator', self._translator_box.currentValue())
        translate.set_service(self._translator_box.currentValue())

    def _on_lang_changed(self):
        self.sm.set('language', self.theme_manager.locale)
        self._apply_lang()


class UpdateWidget(KitTabLayout):
    NO_RELEASE = 0
    READY_TO_DOWNLOAD = 1
    DOWNLOADING = 2
    READY_TO_INSTALL = 3

    clicked = pyqtSignal()
    cancel = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setContentsMargins(0, 0, 0, 0)

        self._button_check = KitButton(KitLocaleString.check_update)
        self._button_check.clicked.connect(self.clicked.emit)
        self.addWidget(self._button_check)

        self._button_download = KitButton(KitLocaleString.download_update)
        self._button_download.clicked.connect(self.clicked.emit)
        self.addWidget(self._button_download)

        progress_layout = KitHBoxLayout()
        progress_layout.spacing = 6
        self.addWidget(progress_layout)

        self._progress_bar = KitProgressBar()
        self._progress_bar.setFixedHeight(24)
        progress_layout.addWidget(self._progress_bar)

        self._button_cancel = KitIconButton('line-ban')
        self._button_cancel.size = 24
        self._button_cancel.clicked.connect(self.cancel.emit)
        progress_layout.addWidget(self._button_cancel)

        self._button_install = KitButton(KitLocaleString.install_update)
        self._button_install.clicked.connect(self.clicked.emit)
        self.addWidget(self._button_install)

    def set_status(self, status):
        self.setCurrent(status)

    def set_progress(self, value):
        self.set_status(UpdateWidget.DOWNLOADING)
        self._progress_bar.setValue(value)
