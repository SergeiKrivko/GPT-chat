from translatepy import Translator as Translator

from translatepy.models import TranslationResult, LanguageResult
from translatepy.translators import *


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


SERVICES = {
    'Google': GoogleTranslate,
    'Google-v1': GoogleTranslateV1,
    'Google-v2': GoogleTranslateV2,
    'Yandex': YandexTranslate,
    'Bing': BingTranslate,
    'Microsoft': MicrosoftTranslate,
    'Deepl': DeeplTranslate,
    'Libre': LibreTranslate,
    'Reverso': ReversoTranslate,
    'MyMemory': MyMemoryTranslate,
    'Translate.com': TranslateComTranslate,
}


_translator: Translator


def set_service(service=None):
    global _translator
    if service:
        _translator = Translator([SERVICES[service]])
    else:
        _translator = Translator()


def translate(text, dest='ru') -> TranslationResult:
    return _translator.translate(text, dest)


def translate_html(text, dest='ru') -> str:
    return _translator.translate_html(text, dest)


def detect(text) -> LanguageResult:
    return _translator.language(text)
