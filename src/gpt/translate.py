from googletrans import Translator
from googletrans.models import Translated

_translator = Translator()


def translate(text, dest='ru') -> Translated:
    return _translator.translate(text, dest=dest)


def detect(text):
    return _translator.detect(text)

