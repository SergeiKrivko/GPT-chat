from PyQtUIkit.themes.locale import KitLocaleString
from PyQtUIkit.widgets import KitMenu
from qasync import asyncSlot

from src.gpt.translate import detect, LANGUAGES
from src.settings_manager import SettingsManager


class ContextMenu(KitMenu):
    DELETE_MESSAGE = 1
    COPY_AS_TEXT = 2
    SELECT_ALL = 3
    SEND_TO_TELEGRAM = 4
    COPY_AS_MARKDOWN = 5
    REPLY = 6
    TRANSLATE = 7
    SHOW_ORIGINAL = 8

    def __init__(self, parent, sm: SettingsManager):
        super().__init__(parent)
        self.action = None
        self.data = None
        self._sm = sm

        action = self.addAction(KitLocaleString.reply, 'custom-reply')
        action.triggered.connect(lambda: self.set_action(ContextMenu.REPLY))

        self.addSeparator()

        # action = self.addAction(KitLocaleString.select_all, 'line-text')
        # action.triggered.connect(lambda: self.set_action(ContextMenu.SELECT_ALL))

        action = self.addAction(KitLocaleString.copy_as_text, 'line-copy')
        action.triggered.connect(lambda: self.set_action(ContextMenu.COPY_AS_TEXT))

        action = self.addAction(KitLocaleString.copy_as_markdown, 'custom-copy-md')
        action.triggered.connect(lambda: self.set_action(ContextMenu.COPY_AS_MARKDOWN))

        self.addSeparator()

        action = self.addAction(KitLocaleString.delete, 'line-trash')
        action.triggered.connect(lambda: self.set_action(ContextMenu.DELETE_MESSAGE))

        self.addSeparator()

        if parent.translated:
            action = self.addAction(KitLocaleString.show_original)
            action.triggered.connect(lambda: self.set_action(ContextMenu.SHOW_ORIGINAL))

        menu = self.addMenu(KitLocaleString.translate_to, 'custom-translate')
        languages = [(key, getattr(KitLocaleString, f'lang_{key}').get(parent.theme_manager).capitalize())
                     for key in LANGUAGES]
        languages.sort(key=lambda x: x[1])
        for key, name in languages:
            action = menu.addAction(name)
            action.triggered.connect(lambda x, lang=key: self.set_action(ContextMenu.TRANSLATE, lang))

        self.detect_lang(parent.message.content)

    @asyncSlot()
    async def detect_lang(self, text):
        try:
            message_lang = await self._sm.run_async(lambda: detect(text), 'detect')
            message_lang = message_lang.result.alpha2
        except Exception:
            message_lang = None

        if message_lang != self.theme_manager.locale:
            action = self.addAction(KitLocaleString.translate_to_locale, 'custom-translate')
            action.triggered.connect(lambda: self.set_action(ContextMenu.TRANSLATE, self.theme_manager.locale))
            self._apply_theme()

    def set_action(self, action, data=None):
        self.action = action
        self.data = data
