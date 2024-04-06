import os
from sys import argv

try:
    from src.secret_config import *
    SECRET_DATA = True
except ImportError:
    SECRET_DATA = False


ORGANISATION_NAME = "SergeiKrivko"
ORGANISATION_URL = "https://github.com/SergeiKrivko/GPT-chat"
APP_NAME = "GPT-chat"
APP_VERSION = "3.5.4"

FIREBASE_API_KEY = "AIzaSyA8z4fe_VedzuLvLQk9HnQTFnVeJDRdxkc"

APP_DIR = os.path.dirname(argv[0])
ASSETS_DIR = os.path.dirname(os.path.dirname(__file__))
