import asyncio

from googletrans import Translator as _Translator
from googletrans.models import Translated
from uuid import uuid4

from src.settings_manager import SettingsManager


class Translator:
    def __init__(self):
        self.sm: SettingsManager = None
        self.translator = _Translator()

    def init(self, sm):
        self.sm = sm

    def async_translate(self, text, dest='ru'):
        return self.sm.run_process(lambda: self.translator.translate(text, dest=dest), f'translate-{uuid4()}')

    def async_detect(self, text):
        return self.sm.run_process(lambda: self.translator.detect(text), f'translate-{uuid4()}')


_translator = Translator()


def init(sm):
    _translator.init(sm)


def translate(text, dest='ru') -> Translated:
    return _translator.translator.translate(text, dest=dest)


async def async_translate(text, dest='ru') -> Translated:
    looper = _translator.async_translate(text, dest=dest)
    while not looper.isFinished():
        await asyncio.sleep(0.2)
    return looper.res


def detect(text):
    return _translator.translator.detect(text)


async def async_detect(text):
    looper = _translator.async_detect(text)
    while not looper.isFinished():
        await asyncio.sleep(0.2)
    return looper.res

