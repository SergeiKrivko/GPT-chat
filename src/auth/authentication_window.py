import asyncio
import json

import aiohttp
from PyQt6.QtCore import Qt, pyqtSignal
from PyQtUIkit.widgets import *
from qasync import asyncSlot

from src import config
from src.auth.oauth import OAuthScreen


class AuthenticationWindow(KitDialog):
    def __init__(self, parent, sm):
        super().__init__(parent)
        self._sm = sm
        self.name = "Авторизация"

        self.setFixedSize(400, 400)

        self._main_layout = KitTabLayout()
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self.setWidget(self._main_layout)

        authorized = self._sm.get('user_id') and self._sm.get('user_email') and self._sm.get('user_token')

        self._sign_in_screen = _SignInScreen(self._sm)
        self._sign_in_screen.signedIn.connect(self._on_signed_in)
        self._sign_in_screen.signUpPressed.connect(self._on_sign_up_pressed)
        self._sign_in_screen.oauthRequested.connect(self._on_oauth_requested)
        self._main_layout.addWidget(self._sign_in_screen)

        self._sign_up_screen = _SignUpScreen(self._sm)
        self._sign_up_screen.signedUp.connect(self._on_signed_in)
        self._sign_up_screen.backPressed.connect(self._on_sign_up_stopped)
        self._main_layout.addWidget(self._sign_up_screen)

        self._verify_email_screen = _VerifyEmailScreen(self._sm)
        self._verify_email_screen.emailVerified.connect(self._on_email_verified)
        self._verify_email_screen.backPressed.connect(self._on_sign_up_stopped)
        self._verify_email_screen.hide()
        self._main_layout.addWidget(self._verify_email_screen)

        self._oauth_screen = OAuthScreen(self._sm)
        self._oauth_screen.signedIn.connect(self._on_signed_in)
        self._oauth_screen.backPressed.connect(self._on_sign_up_stopped)
        self._main_layout.addWidget(self._oauth_screen)

        self._signed_screen = _SignedScreen(self._sm)
        self._signed_screen.exitAccount.connect(self._on_exit_account)
        self._main_layout.addWidget(self._signed_screen)

        if authorized:
            self._main_layout.setCurrent(4)

    def _on_exit_account(self):
        self._main_layout.setCurrent(0)

    def _on_signed_in(self):
        self._on_signed_in_async()

    @asyncSlot()
    async def _on_signed_in_async(self):
        email_verified = await _VerifyEmailScreen.check_email_verified(self._sm.get('user_token'))
        if email_verified:
            self._on_email_verified()
        else:
            self._main_layout.setCurrent(2)
            self._verify_email_screen.update_user()
            self._verify_email_screen.show()

    def _on_email_verified(self):
        self._signed_screen.update_account()
        self._main_layout.setCurrent(4)

    def _on_sign_up_stopped(self):
        self._main_layout.setCurrent(0)

    def _on_oauth_requested(self, provider):
        self._main_layout.setCurrent(3)
        self._oauth_screen.auth(provider)

    def _on_sign_up_pressed(self):
        self._main_layout.setCurrent(1)


class _SignInScreen(KitVBoxLayout):
    signedIn = pyqtSignal()
    signUpPressed = pyqtSignal()
    oauthRequested = pyqtSignal(str)

    def __init__(self, sm):
        super().__init__()
        self._sm = sm

        self.setContentsMargins(70, 20, 70, 20)
        self.setSpacing(5)

        self._main_layout = KitVBoxLayout()
        self._main_layout.setSpacing(6)
        self._main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.addWidget(self._main_layout)

        label = KitLabel("Email:")
        self._main_layout.addWidget(label)

        self._email_edit = KitLineEdit(self._sm.get('user_email', ''))
        self._email_edit.font_size = 'big'
        self._email_edit.setFixedHeight(34)
        self._email_edit.returnPressed.connect(self.sign_in)
        self._main_layout.addWidget(self._email_edit)

        label = KitLabel("Пароль:")
        self._main_layout.addWidget(label)

        self._password_edit = KitLineEdit()
        self._password_edit.font_size = 'big'
        self._password_edit.setFixedHeight(34)
        self._password_edit.setEchoMode(KitLineEdit.EchoMode.Password)
        self._password_edit.returnPressed.connect(self.sign_in)
        self._main_layout.addWidget(self._password_edit)

        self._error_label = KitLabel()
        self._error_label.main_palette = 'DangerText'
        self._error_label.setWordWrap(True)
        self._main_layout.addWidget(self._error_label)

        bottom_layout = KitHBoxLayout()
        bottom_layout.setContentsMargins(0, 10, 0, 10)
        bottom_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._main_layout.addWidget(bottom_layout)

        self._button_join = KitButton("Войти")
        self._button_join.radius = 8
        self._button_join.font_size = 'big'
        self._button_join.setFixedSize(256, 50)
        self._button_join.clicked.connect(self.sign_in)
        bottom_layout.addWidget(self._button_join)

        self._button_reset_password = KitButton("Сбросить пароль")
        self._button_reset_password.main_palette = 'Transparent'
        self._button_reset_password.border = 0
        self._button_reset_password.clicked.connect(self.reset_password)
        self._button_reset_password.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._main_layout.addWidget(self._button_reset_password)

        self._button_sign_up = KitButton("Регистрация")
        self._button_sign_up.main_palette = 'Transparent'
        self._button_sign_up.border = 0
        self._button_sign_up.clicked.connect(self.signUpPressed.emit)
        self._button_sign_up.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._main_layout.addWidget(self._button_sign_up)

        oauth_layout = KitHBoxLayout()
        oauth_layout.setSpacing(6)
        oauth_layout.addWidget(label := KitLabel("Войти через:"))
        label.setWordWrap(True)
        self._main_layout.addWidget(oauth_layout)

        for el in ['google', 'github', 'apple', 'microsoft']:
            button = KitIconButton(f'brands-{el}')
            button.size = 40
            button.clicked.connect(lambda x,  provider=el: self.oauthRequested.emit(provider))
            oauth_layout.addWidget(button)

        self._spinner = KitHBoxLayout()
        self.addWidget(self._spinner)
        self._spinner.hide()

        spinner = KitSpinner()
        spinner.size = 46
        self._spinner.addWidget(spinner)

    @asyncSlot()
    async def sign_in(self):
        rest_api_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword" \
                       f"?key={config.FIREBASE_API_KEY}"
        self.show_spinner(True)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(rest_api_url, data={"email": self._email_edit.text(),
                                                            "password": self._password_edit.text(),
                                                            "returnSecureToken": True}) as r:
                    res = await r.json()
                    if r.ok:
                        self._sm.set('user_email', res['email'])
                        self._sm.set('user_token', res['idToken'])
                        self._sm.set('user_refresh_token', res['refreshToken'])
                        self._sm.set('user_id', res['localId'])
                        self._sm.authorized = True
                        self.signedIn.emit()
                    else:
                        match res.get('error', dict()).get('message'):
                            case 'INVALID_LOGIN_CREDENTIALS':
                                self.show_error("Неверный логин или пароль")
                            case 'INVALID_EMAIL':
                                self.show_error("Некорректный email")
                            case 'MISSING_PASSWORD':
                                self.show_error("Введите пароль")
                            case _:
                                self.show_error("Неизвестная ошибка")
                                print(res)
                self._password_edit.clear()
        except aiohttp.ClientConnectionError:
            self.show_error("Нет подключения к интернету")
        except Exception as ex:
            self.show_error(f"Неизвестная ошибка: {ex.__class__.__name__}: {ex}")
        self.show_spinner(False)

    def reset_password(self):
        self._reset_password()

    @asyncSlot()
    async def _reset_password(self):
        request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/getOobConfirmationCode?key={0}".format(
            config.FIREBASE_API_KEY)
        data = json.dumps({"requestType": "PASSWORD_RESET", "email": self._email_edit.text()})
        async with aiohttp.ClientSession() as session:
            async with session.post(request_ref, data=data) as resp:
                res = await resp.text()
                if not resp.ok:
                    print(res)

    def show_spinner(self, flag):
        self._spinner.setHidden(not flag)
        self._main_layout.setHidden(flag)

    def show_error(self, text):
        self._error_label.setText(text)

    def show(self) -> None:
        super().show()
        self.hide_error()

    def hide_error(self):
        self._error_label.setText("")


class _SignUpScreen(KitVBoxLayout):
    signedUp = pyqtSignal()
    backPressed = pyqtSignal()

    def __init__(self, sm):
        super().__init__()
        self._sm = sm

        self.setContentsMargins(70, 20, 70, 20)
        self.setSpacing(5)

        self._main_layout = KitVBoxLayout()
        self._main_layout.setSpacing(6)
        self._main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.addWidget(self._main_layout)

        label = KitLabel("Email:")
        self._main_layout.addWidget(label)

        self._email_edit = KitLineEdit(self._sm.get('user_email', ''))
        self._email_edit.font_size = 'big'
        self._email_edit.setFixedHeight(34)
        self._email_edit.returnPressed.connect(self.sign_up)
        self._main_layout.addWidget(self._email_edit)

        label = KitLabel("Пароль:")
        self._main_layout.addWidget(label)

        self._password_edit = KitLineEdit()
        self._password_edit.font_size = 'big'
        self._password_edit.setFixedHeight(34)
        self._password_edit.setEchoMode(KitLineEdit.EchoMode.Password)
        self._password_edit.returnPressed.connect(self.sign_up)
        self._main_layout.addWidget(self._password_edit)

        label = KitLabel("Пароль еще раз:")
        self._main_layout.addWidget(label)

        self._password_edit2 = KitLineEdit()
        self._password_edit2.font_size = 'big'
        self._password_edit2.setFixedHeight(34)
        self._password_edit2.setEchoMode(KitLineEdit.EchoMode.Password)
        self._password_edit2.returnPressed.connect(self.sign_up)
        self._main_layout.addWidget(self._password_edit2)

        self._error_label = KitLabel()
        self._error_label.main_palette = 'DangerText'
        self._error_label.setWordWrap(True)
        self._main_layout.addWidget(self._error_label)

        bottom_layout = KitHBoxLayout()
        bottom_layout.setContentsMargins(0, 10, 0, 10)
        bottom_layout.setSpacing(6)
        bottom_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._main_layout.addWidget(bottom_layout)

        # self._button_back = KitButton("Назад")
        self._button_back = KitIconButton('solid-arrow-left')
        self._button_back.radius = 8
        self._button_back.size = 50
        self._button_back.setContentsMargins(10, 10, 10, 10)
        # self._button_back.setFixedSize(150, 30)
        self._button_back.clicked.connect(self.backPressed.emit)
        bottom_layout.addWidget(self._button_back)

        self._button_sign_up = KitButton("Создать аккаунт")
        self._button_sign_up.radius = 8
        self._button_sign_up.setFixedSize(200, 50)
        self._button_sign_up.clicked.connect(self.sign_up)
        bottom_layout.addWidget(self._button_sign_up)

        self._spinner = KitHBoxLayout()
        self.addWidget(self._spinner)
        self._spinner.hide()

        spinner = KitSpinner()
        spinner.size = 46
        self._spinner.addWidget(spinner)

    def sign_up(self):
        self._sign_up()

    @asyncSlot()
    async def _sign_up(self):
        if self._password_edit.text() != self._password_edit2.text():
            self.show_error("Пароли не совпадают")
            return
        rest_api_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={config.FIREBASE_API_KEY}"
        self.show_spinner(True)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(rest_api_url, data={"email": self._email_edit.text(),
                                                            "password": self._password_edit.text(),
                                                            "returnSecureToken": True}) as r:
                    res = await r.json()
                    if r.ok:
                        self._sm.set('user_email', res['email'])
                        self._sm.set('user_token', res['idToken'])
                        self._sm.set('user_refresh_token', res['refreshToken'])
                        self._sm.set('user_id', res['localId'])
                        self._sm.authorized = True
                        self.signedUp.emit()
                    else:
                        match res.get('error', dict()).get('message'):
                            case 'EMAIL_EXISTS':
                                self.show_error("Аккаунт уже существует")
                            case 'MISSING_EMAIL':
                                self.show_error("Введите email")
                            case 'MISSING_PASSWORD':
                                self.show_error("Введите пароль")
                            case 'INVALID_EMAIL':
                                self.show_error("Некорректный email")
                            case 'WEAK_PASSWORD : Password should be at least 6 characters':
                                self.show_error("Слишком короткий пароль")
                            case _:
                                self.show_error("Неизвестная ошибка")
                                print(res)
        except aiohttp.ClientConnectionError:
            self.show_error("Нет подключения к интернету")
        except Exception as ex:
            self.show_error(f"Неизвестная ошибка: {ex.__class__.__name__}: {ex}")
        self.show_spinner(False)

    def show_spinner(self, flag):
        self._spinner.setHidden(not flag)
        self._main_layout.setHidden(flag)

    def show_error(self, text):
        self._error_label.setText(text)


class _VerifyEmailScreen(KitVBoxLayout):
    emailVerified = pyqtSignal()
    backPressed = pyqtSignal()

    def __init__(self, sm):
        super().__init__()
        self._sm = sm

        self.setContentsMargins(20, 20, 20, 20)
        self.setSpacing(5)

        self._label = KitLabel()
        self._label.setWordWrap(True)
        self.addWidget(self._label)

        bottom_layout = KitHBoxLayout()
        bottom_layout.setContentsMargins(0, 20, 0, 0)
        bottom_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.addWidget(bottom_layout)

        self._button_back = KitButton("Назад")
        self._button_back.setFixedSize(150, 50)
        self._button_back.clicked.connect(self._exit)
        bottom_layout.addWidget(self._button_back)

        self._button_send_again = KitButton("Отправить еще раз")
        self._button_send_again.setFixedSize(150, 50)
        self._button_send_again.clicked.connect(lambda: self.send_email_verification(self._sm.get('user_token')))
        bottom_layout.addWidget(self._button_send_again)

    def update_user(self):
        self._label.setText(f"На ваш адрес {self._sm.get('user_email', '<Ошибка>')} было отправлено письмо. "
                            f"Перейдите по ссылке в этом письме, чтобы подтвердить адрес электронной почты.")
        self.send_email_verification(self._sm.get('user_token'))
        self.wait_while_email_verified(self._sm.get('user_token'))

    def _exit(self):
        self._email_waiting = False
        self.backPressed.emit()

    @asyncSlot()
    async def send_email_verification(self, id_token):
        request_ref = f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/getOobConfirmationCode?key={config.FIREBASE_API_KEY}"
        data = {"requestType": "VERIFY_EMAIL", "idToken": id_token}
        async with aiohttp.ClientSession() as session:
            async with session.post(request_ref, data=data) as resp:
                if not resp.ok:
                    print(resp.text)

    @staticmethod
    async def get_account_info(id_token):
        request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/getAccountInfo?key={0}".format(
            config.FIREBASE_API_KEY)
        data = json.dumps({"idToken": id_token})
        async with aiohttp.ClientSession() as session:
            async with session.post(request_ref, data=data) as resp:
                res = await resp.text()
                if not resp.ok:
                    print(res)
                    raise aiohttp.ClientConnectionError
        return json.loads(res)

    @staticmethod
    async def check_email_verified(id_token):
        info = await _VerifyEmailScreen.get_account_info(id_token)
        try:
            return info['users'][0]['emailVerified']
        except aiohttp.ClientConnectionError:
            return False
        except KeyError:
            return False

    @asyncSlot()
    async def wait_while_email_verified(self, id_token):
        self._email_waiting = True
        while self._email_waiting:
            await asyncio.sleep(2)
            verified = await self.check_email_verified(id_token)
            if verified:
                self.emailVerified.emit()
                return True
        return False


class _SignedScreen(KitVBoxLayout):
    exitAccount = pyqtSignal()

    def __init__(self, sm):
        super().__init__()
        self._sm = sm

        self.setContentsMargins(20, 20, 20, 20)
        self.setSpacing(5)

        self._label = KitLabel()
        self._label.font_size = 'big'
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_account()
        self.addWidget(self._label)

        bottom_layout = KitHBoxLayout()
        bottom_layout.setContentsMargins(0, 20, 0, 0)
        bottom_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.addWidget(bottom_layout)

        self._button_exit = KitButton("Выйти")
        self._button_exit.radius = 8
        self._button_exit.font_size = 'big'
        self._button_exit.setFixedSize(150, 50)
        self._button_exit.clicked.connect(self.exit_account)
        bottom_layout.addWidget(self._button_exit)

    def exit_account(self):
        self.exitAccount.emit()
        self._sm.set('user_id', '')
        self._sm.set('user_email', '')
        self._sm.set('user_token', '')

    def update_account(self):
        self._label.setText(self._sm.get('user_email', ''))
