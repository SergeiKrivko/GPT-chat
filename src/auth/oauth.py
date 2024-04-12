import asyncio
import webbrowser
from time import time
from typing import Literal

import aiohttp
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import QApplication
from PyQtUIkit.core import KitFont
from PyQtUIkit.widgets import *
from qasync import asyncSlot

from src import config
from src.settings_manager import SettingsManager


class OAuthScreen(KitVBoxLayout):
    signedIn = pyqtSignal()
    backPressed = pyqtSignal()

    def __init__(self, sm: SettingsManager):
        super().__init__()
        self._sm = sm
        self._provider = ''
        self._url = ''
        self._provider_data = ''
        self.setContentsMargins(70, 20, 70, 20)
        self.setSpacing(10)
        self.setAlignment(Qt.AlignmentFlag.AlignTop)

        top_layout = KitHBoxLayout()
        top_layout.setSpacing(10)
        self.addWidget(top_layout)

        button_back = KitIconButton('line-arrow-back')
        button_back.size = 40
        top_layout.addWidget(button_back)
        button_back.clicked.connect(self.backPressed.emit)

        self._top_label = KitLabel()
        top_layout.addWidget(self._top_label)

        self._tab_layout = KitTabLayout()
        self._tab_layout.setContentsMargins(0, 0, 0, 0)
        self.addWidget(self._tab_layout)

        self._spinner = KitHBoxLayout()
        self._tab_layout.addWidget(self._spinner)
        self._spinner.hide()

        spinner = KitSpinner()
        spinner.size = 46
        self._spinner.addWidget(spinner)

        self._error = KitLabel()
        self._error.main_palette = 'Danger'
        self._tab_layout.addWidget(self._error)

        self._code = KitVBoxLayout()
        self._code.setSpacing(10)
        self._tab_layout.addWidget(self._code)

        self._code.addWidget(label := KitLabel("Скопируйте код и перейдите по ссылке"))
        label.setWordWrap(True)

        group = KitHGroup()
        group.setFixedWidth(250)
        group.radius = 8
        group.height = 40
        self._code.addWidget(group)

        self._code_label = KitLineEdit()
        self._code_label.setReadOnly(True)
        group.addItem(self._code_label)

        button = KitIconButton('line-copy')
        button.clicked.connect(self.open_url)
        group.addItem(button)

        link = KitVBoxLayout()
        link.setSpacing(8)
        self._tab_layout.addWidget(link)

        link.addWidget(KitLabel("Email:"))
        self._email_line = KitLineEdit('')
        self._email_line.setFixedHeight(34)
        self._email_line.font_size = KitFont.Size.BIG
        self._email_line.setReadOnly(True)
        link.addWidget(self._email_line)

        link.addWidget(KitLabel("Пароль:"))
        self._password_line = KitLineEdit('')
        self._password_line.setFixedHeight(34)
        self._password_line.setEchoMode(KitLineEdit.EchoMode.Password)
        self._password_line.font_size = KitFont.Size.BIG
        link.addWidget(self._password_line)

        self._error_line = KitLabel()
        self._error_line.main_palette = 'Danger'
        link.addWidget(self._error_line)

        button = KitButton("Войти")
        button.setFixedSize(256, 50)
        button.clicked.connect(lambda: self._try_link())
        link.addWidget(button)

        self.show_spinner()

    def show_error(self, text: str):
        self._tab_layout.setCurrent(1)
        self._error.setText(text)

    def show_password_error(self, text: str):
        self._tab_layout.setCurrent(3)
        self._error_line.setText(text)

    def show_spinner(self):
        self._tab_layout.setCurrent(0)

    def show_code(self, code: str, url=''):
        self._tab_layout.setCurrent(2)
        self._url = url
        self._code_label.setText(code)

    def show_link(self, email):
        self._error_line.setText('')
        self._email_line.setText(email)
        self._tab_layout.setCurrent(3)

    def open_url(self):
        QApplication.clipboard().setText(self._code_label.text())
        if self._url:
            webbrowser.open(self._url)

    def auth(self, provider: Literal['google', 'github', 'apple', 'microsoft']):
        self._top_label.setText(f"Вход через {provider.upper()}")
        self._provider = provider
        match provider:
            case 'github':
                self.auth_with_github()
            case 'google':
                self.auth_with_google()
            case _:
                KitDialog.warning(self, "Ошибка", "Данный метод авторизации пока не поддерживается")

    @asyncSlot()
    async def auth_with_google(self):
        try:
            if not config.SECRET_DATA:
                self.show_error("Авторизация через Google не поддерживается в данной версии приложения")
                return

            from google_auth_oauthlib.flow import InstalledAppFlow

            flow = InstalledAppFlow.from_client_config(
                config.GOOGLE_OAUTH_SECRETS,
                scopes=['openid', 'https://www.googleapis.com/auth/userinfo.email'])

            def run_local_server():
                flow.run_local_server(port=2000)
                self._provider_data = f"id_token={flow.oauth2session.token['id_token']}&providerId=google.com"

            thread = self._sm.run_process(run_local_server, 'oauth-google')
            thread.finished.connect(lambda: self.sign_in())

        except aiohttp.ClientConnectionError:
            self.show_error("Нет подключения к интернету")
        except Exception as ex:
            self.show_error(f"{ex.__class__.__name__}: {ex}")

    @asyncSlot()
    async def auth_with_github(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://github.com/login/device/code", data={
                    'client_id': "7decbb82487a74f76e04",
                    'scope': ['user:email'],
                }, headers={'Accept': 'application/json'}) as resp:
                    res = await resp.json()
                    if not resp.ok:
                        self.show_spinner()
                        self.show_error(res['error'])
                        return

                device_code = res['device_code']
                expires_in = time() + int(res['expires_in'])
                self.show_code(res['user_code'], res['verification_uri'])

                while time() < expires_in:
                    async with session.post("https://github.com/login/oauth/access_token", data={
                        'client_id': "7decbb82487a74f76e04",
                        'device_code': device_code,
                        'grant_type': "urn:ietf:params:oauth:grant-type:device_code",
                    }, headers={'Accept': 'application/json'}) as resp:
                        res = await resp.json()
                        if 'access_token' in res:
                            break
                        await asyncio.sleep(10)
                else:
                    self.show_spinner()
                    self.show_error("Время действия кода иссякло")
                    return

                self._provider_data = f"access_token={res['access_token']}&providerId=github.com"
                await self._sign_in()
        except aiohttp.ClientConnectionError:
            self.show_error("Нет подключения к интернету")
        except Exception as ex:
            self.show_error(f"{ex.__class__.__name__}: {ex}")

    @asyncSlot()
    async def sign_in(self):
        await self._sign_in()

    async def _sign_in(self):
        try:
            async with aiohttp.ClientSession() as session:
                rest_api_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp" \
                               f"?key={config.FIREBASE_API_KEY}"
                async with session.post(rest_api_url, data={
                    "postBody": self._provider_data,
                    "requestUri": "http://localhost",
                    "returnIdpCredential": True,
                    "returnSecureToken": True
                }) as resp:
                    res = await resp.json()
                    if resp.ok:
                        if res.get('needConfirmation'):
                            self.show_link(res['email'])
                            return
                        self._sm.set('user_email', res['email'])
                        self._sm.set('user_token', res['idToken'])
                        self._sm.set('user_refresh_token', res['refreshToken'])
                        self._sm.set('user_id', res['localId'])
                        self._sm.authorized = True
                        self.signedIn.emit()
                    else:
                        print(res.get('error', dict()).get('message'))
                        self.show_error(res.get('error', dict()).get('message'))
        except aiohttp.ClientConnectionError:
            self.show_error("Нет подключения к интернету")
        except Exception as ex:
            self.show_error(f"{ex.__class__.__name__}: {ex}")

    @asyncSlot()
    async def _try_link(self):
        try:
            self.show_spinner()
            async with aiohttp.ClientSession() as session:
                rest_api_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword" \
                               f"?key={config.FIREBASE_API_KEY}"
                async with session.post(rest_api_url, data={"email": self._email_line.text(),
                                                            "password": self._password_line.text(),
                                                            "returnSecureToken": True}) as r:
                    res = await r.json()
                    if r.ok:
                        token = res['idToken']
                    else:
                        match res.get('error', dict()).get('message'):
                            case 'INVALID_LOGIN_CREDENTIALS':
                                self.show_password_error("Неверный логин или пароль")
                            case 'INVALID_EMAIL':
                                self.show_password_error("Некорректный email")
                            case 'MISSING_PASSWORD':
                                self.show_password_error("Введите пароль")
                            case _:
                                self.show_password_error(res.get('error', dict()).get('message'))
                        return

                rest_api_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp" \
                               f"?key={config.FIREBASE_API_KEY}"
                async with session.post(rest_api_url, data={
                    "postBody": self._provider_data,
                    "idToken": token,
                    "requestUri": "http://localhost",
                    "returnIdpCredential": True,
                    "returnSecureToken": True
                }) as resp:
                    res = await resp.json()
                    if resp.ok:
                        self._sm.set('user_email', res['email'])
                        self._sm.set('user_token', res['idToken'])
                        self._sm.set('user_refresh_token', res['refreshToken'])
                        self._sm.set('user_id', res['localId'])
                        self._sm.authorized = True
                        self.signedIn.emit()
                    else:
                        self.show_error(res.get('error', dict()).get('message'))
        except aiohttp.ClientConnectionError:
            self.show_error("Нет подключения к интернету")
        except Exception as ex:
            self.show_error(f"{ex.__class__.__name__}: {ex}")
