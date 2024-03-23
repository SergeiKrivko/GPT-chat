import asyncio
import json

import aiohttp
import requests
from PyQt6.QtCore import Qt, pyqtSignal
from PyQtUIkit.widgets import *
from qasync import asyncSlot

from src import config


class AuthenticationWindow(KitDialog):
    def __init__(self, parent, sm):
        super().__init__(parent)
        self._sm = sm
        self.name = "Авторизация"

        self.setFixedSize(350, 330)

        main_layout = KitHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setWidget(main_layout)

        authorized = self._sm.get('user_id') and self._sm.get('user_email') and self._sm.get('user_token')

        self._sign_in_screen = _SignInScreen(self._sm)
        self._sign_in_screen.signedIn.connect(self._on_signed_in)
        self._sign_in_screen.signUpPressed.connect(self._on_sign_up_pressed)
        if authorized:
            self._sign_in_screen.hide()
        main_layout.addWidget(self._sign_in_screen)

        self._sign_up_screen = _SignUpScreen(self._sm)
        self._sign_up_screen.signedUp.connect(self._on_signed_in)
        self._sign_up_screen.backPressed.connect(self._on_sign_up_stopped)
        self._sign_up_screen.hide()
        main_layout.addWidget(self._sign_up_screen)

        self._verify_email_screen = _VerifyEmailScreen(self._sm)
        self._verify_email_screen.emailVerified.connect(self._on_email_verified)
        self._verify_email_screen.backPressed.connect(self._on_sign_up_stopped)
        self._verify_email_screen.hide()
        main_layout.addWidget(self._verify_email_screen)

        self._signed_screen = _SignedScreen(self._sm)
        self._signed_screen.exitAccount.connect(self._on_exit_account)
        if not authorized:
            self._signed_screen.hide()
        main_layout.addWidget(self._signed_screen)

    def _on_exit_account(self):
        self._signed_screen.hide()
        self._sign_in_screen.show()

    def _on_signed_in(self):
        self._on_signed_in_async()

    @asyncSlot()
    async def _on_signed_in_async(self):
        self._sign_up_screen.hide()
        self._sign_in_screen.hide()

        email_verified = await _VerifyEmailScreen.check_email_verified(self._sm.get('user_token'))
        if email_verified:
            self._on_email_verified()
        else:
            self._verify_email_screen.update_user()
            self._verify_email_screen.show()

    def _on_email_verified(self):
        self._verify_email_screen.hide()
        self._signed_screen.update_account()
        self._signed_screen.show()

    def _on_sign_up_stopped(self):
        self._sign_up_screen.hide()
        self._verify_email_screen.hide()
        self._sign_in_screen.show()

    def _on_sign_up_pressed(self):
        self._sign_in_screen.hide()
        self._sign_up_screen.show()


class _SignInScreen(KitVBoxLayout):
    signedIn = pyqtSignal()
    signUpPressed = pyqtSignal()

    def __init__(self, sm):
        super().__init__()
        self._sm = sm

        self.setContentsMargins(20, 20, 20, 20)
        self.setSpacing(5)

        top_layout = KitHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.addWidget(top_layout)

        self._button_reset_password = KitButton("Сбросить пароль")
        self._button_reset_password.setFixedSize(150, 35)
        self._button_reset_password.clicked.connect(self.reset_password)
        self._button_reset_password.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        top_layout.addWidget(self._button_reset_password)

        self._button_sign_up = KitButton("Регистрация")
        self._button_sign_up.setFixedSize(120, 35)
        self._button_sign_up.clicked.connect(self.signUpPressed.emit)
        self._button_sign_up.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        top_layout.addWidget(self._button_sign_up)

        label = KitLabel("Email:")
        self.addWidget(label)

        self._email_edit = KitLineEdit(self._sm.get('user_email', ''))
        self._email_edit.font_size = 'big'
        self._email_edit.returnPressed.connect(self.sign_in)
        self.addWidget(self._email_edit)

        label = KitLabel("Пароль:")
        self.addWidget(label)

        self._password_edit = KitLineEdit()
        self._password_edit.font_size = 'big'
        self._password_edit.setEchoMode(KitLineEdit.EchoMode.Password)
        self._password_edit.returnPressed.connect(self.sign_in)
        self.addWidget(self._password_edit)

        self._error_label = KitLabel()
        self._error_label.main_palette = 'DangerText'
        self._error_label.setWordWrap(True)
        self.addWidget(self._error_label)

        bottom_layout = KitHBoxLayout()
        bottom_layout.setContentsMargins(0, 15, 0, 0)
        bottom_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.addWidget(bottom_layout)

        self._button_join = KitButton("Войти")
        self._button_join.radius = 8
        self._button_join.font_size = 'big'
        self._button_join.setFixedSize(150, 50)
        self._button_join.clicked.connect(self.sign_in)
        bottom_layout.addWidget(self._button_join)

    def sign_in(self):
        rest_api_url = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"

        try:
            r = requests.post(rest_api_url,
                              params={"key": config.FIREBASE_API_KEY},
                              data=json.dumps({"email": self._email_edit.text(),
                                               "password": self._password_edit.text(),
                                               "returnSecureToken": True}))

            res = json.loads(r.text)
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
                    case _:
                        self.show_error("Неизвестная ошибка")
                        print(r.text)
                self._password_edit.clear()
        except requests.ConnectionError:
            self.show_error("Нет подключения к интернету")
        except Exception as ex:
            self.show_error(f"Неизвестная ошибка: {ex.__class__.__name__}: {ex}")

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

        self.setContentsMargins(20, 20, 20, 20)
        self.setSpacing(5)

        label = KitLabel("Email:")
        self.addWidget(label)

        self._email_edit = KitLineEdit(self._sm.get('user_email', ''))
        self._email_edit.font_size = 'big'
        self._email_edit.returnPressed.connect(self.sign_up)
        self.addWidget(self._email_edit)

        label = KitLabel("Пароль:")
        self.addWidget(label)

        self._password_edit = KitLineEdit()
        self._password_edit.font_size = 'big'
        self._password_edit.setEchoMode(KitLineEdit.EchoMode.Password)
        self._password_edit.returnPressed.connect(self.sign_up)
        self.addWidget(self._password_edit)

        label = KitLabel("Пароль еще раз:")
        self.addWidget(label)

        self._password_edit2 = KitLineEdit()
        self._password_edit2.font_size = 'big'
        self._password_edit2.setEchoMode(KitLineEdit.EchoMode.Password)
        self._password_edit2.returnPressed.connect(self.sign_up)
        self.addWidget(self._password_edit2)

        bottom_layout = KitHBoxLayout()
        bottom_layout.setContentsMargins(0, 20, 0, 0)
        bottom_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.addWidget(bottom_layout)

        self._button_back = KitButton("Назад")
        self._button_back.setFixedSize(150, 50)
        self._button_back.clicked.connect(self.backPressed.emit)
        bottom_layout.addWidget(self._button_back)

        self._button_sign_up = KitButton("Создать аккаунт")
        self._button_sign_up.radius = 8
        self._button_sign_up.setFixedSize(150, 50)
        self._button_sign_up.clicked.connect(self.sign_up)
        bottom_layout.addWidget(self._button_sign_up)

    def sign_up(self):
        self._sign_up()

    @asyncSlot()
    async def _sign_up(self):
        if len(self._password_edit.text()) < 6 or self._password_edit.text() != self._password_edit2.text():
            return

        rest_api_url = "https://identitytoolkit.googleapis.com/v1/accounts:signUp"
        r = requests.post(rest_api_url,
                          params={"key": config.FIREBASE_API_KEY},
                          data=json.dumps({"email": self._email_edit.text(),
                                           "password": self._password_edit.text(),
                                           "returnSecureToken": True}))
        if r.ok:
            res = json.loads(r.text)
            self._sm.set('user_email', res['email'])
            self._sm.set('user_token', res['idToken'])
            self._sm.set('user_refresh_token', res['refreshToken'])
            self._sm.set('user_id', res['localId'])
            self._sm.authorized = True
            self.signedUp.emit()
        else:
            print(r.text)
            self._password_edit.clear()


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

    @staticmethod
    def send_email_verification(id_token):
        request_ref = f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/getOobConfirmationCode?key={config.FIREBASE_API_KEY}"
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps({"requestType": "VERIFY_EMAIL", "idToken": id_token})
        resp = requests.post(request_ref, headers=headers, data=data)
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
                    raise aiohttp.ClientConnectionError
        return json.loads(res)

    @staticmethod
    async def check_email_verified(id_token):
        info = await _VerifyEmailScreen.get_account_info(id_token)
        try:
            return info['users'][0]['emailVerified']
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
