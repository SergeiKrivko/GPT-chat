import asyncio

from translatepy import Translator as _Translator, Language
from uuid import uuid4

from translatepy.models import TranslationResult, LanguageResult

from src.settings_manager import SettingsManager


LANGUAGES = {
    'af',
    'sq',
    'am',
    'ar',
    'hy',
    'az',
    'eu',
    'be',
    'bn',
    'bs',
    'bg',
    'ca',
    'ceb',
    'ny',
    'zh',
    'co',
    'hr',
    'cs',
    'da',
    'nl',
    'en',
    'eo',
    'et',
    'tl',
    'fi',
    'fr',
    'fy',
    'gl',
    'ka',
    'de',
    'el',
    'gu',
    'ht',
    'ha',
    'haw',
    'he',
    'hi',
    'hmn',
    'hu',
    'is',
    'ig',
    'id',
    'ga',
    'it',
    'ja',
    'kn',
    'kk',
    'km',
    'ko',
    'ku',
    'ky',
    'lo',
    'la',
    'lv',
    'lt',
    'lb',
    'mk',
    'mg',
    'ms',
    'ml',
    'mt',
    'mi',
    'mr',
    'mn',
    'my',
    'ne',
    'no',
    'or',
    'ps',
    'fa',
    'pl',
    'pt',
    'pa',
    'ro',
    'ru',
    'sm',
    'gd',
    'sr',
    'st',
    'sn',
    'sd',
    'si',
    'sk',
    'sl',
    'so',
    'es',
    'su',
    'sw',
    'sv',
    'tg',
    'ta',
    'te',
    'th',
    'tr',
    'uk',
    'ur',
    'ug',
    'uz',
    'vi',
    'cy',
    'xh',
    'yi',
    'yo',
    'zu',
}


class Translator:
    def __init__(self):
        self.sm: SettingsManager = None
        self.translator = _Translator()

    def init(self, sm):
        self.sm = sm

    def async_translate(self, text, dest='ru'):
        return self.sm.run_process(lambda: self.translator.translate(text, dest), f'translate-{uuid4()}')

    def async_detect(self, text):
        return self.sm.run_process(lambda: self.translator.language(text), f'translate-{uuid4()}')


_translator = Translator()


def init(sm):
    _translator.init(sm)


def translate(text, dest='ru') -> TranslationResult:
    return _translator.translator.translate(text, dest)


async def async_translate(text, dest='ru') -> TranslationResult:
    looper = _translator.async_translate(text, dest=dest)
    while not looper.isFinished():
        await asyncio.sleep(0.2)
    return looper.res


def detect(text) -> LanguageResult:
    return _translator.translator.language(text)


async def async_detect(text) -> LanguageResult:
    looper = _translator.async_detect(text)
    while not looper.isFinished():
        await asyncio.sleep(0.2)
    return looper.res

