import asyncio
import os.path
import time
from uuid import uuid4

import aiohttp
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from qasync import asyncSlot

from src.database.database import Database
from src.database.firebase import Firebase, FirebaseError
from src.gpt.chat import GPTChat
from src.settings_manager import SettingsManager


class ChatManager(QObject):
    newChat = pyqtSignal(object)
    newChats = pyqtSignal(list)
    deleteChat = pyqtSignal(object)
    deleteRemoteChat = pyqtSignal(object)
    updateChat = pyqtSignal(object)
    newMessage = pyqtSignal(object, object)
    deleteMessage = pyqtSignal(object, object)
    connectionErrorOccurred = pyqtSignal()

    def __init__(self, sm: SettingsManager):
        super().__init__()
        self._sm = sm
        self._database = Database(self._sm)
        self._firebase = Firebase(self._sm)
        self._user_id = ""
        self._user_token = None

    @asyncSlot()
    async def auth(self):
        await self._firebase.auth()
        self._database.update_user()
        await self._load_chats()

        await asyncio.sleep(1)

        if self._firebase.authorized:
            self._load_events()
        self.retry_auth()

    def retry_auth(self):
        if not self._sm.get('user_id'):
            return
        self._retry_auth()

    @asyncSlot()
    async def _retry_auth(self):
        while True:
            if self._firebase.authorized:
                await asyncio.sleep(max(0, self._firebase.expires_in - 20))
            else:
                await asyncio.sleep(3)
            await self._firebase.auth()

            if self._firebase.authorized:
                await self._load_remote_chats()
                await asyncio.sleep(1)
                self._load_events()

    async def _load_chats(self):
        self.newChats.emit(self._database.chats)

        if self._firebase.authorized:
            await self._load_remote_chats()

    def _load_events(self):
        looper = Looper(self._firebase)
        looper.event.connect(self._on_event)
        self._sm.run_process(looper, 'firebase-events')

    async def _load_remote_chats(self):
        looper = ChatsLooper(self._firebase)
        looper.event.connect(self._on_remote_chats)
        self._sm.run_process(looper, 'firebase-chats')

        for chat in self._database.chats:
            if not chat.remote_id:
                continue
            flag = await self._firebase.get(f'chats/{chat.remote_id}')
            if not flag:
                self.deleteRemoteChat.emit(chat)

    def _on_remote_chats(self, path, data):
        if path == '/':
            if data is None:
                return
            for remote_id in data:
                self._add_remote_chat(remote_id)

        else:
            remote_id = path.split('/')[0]
            if path.count('/') > 1:
                chat = self._database.get_by_remote_id(remote_id)
                key = path.split('/')[1]
                self._update_chat_filed(chat, key, data)
            elif data is None:
                chat = self._database.get_by_remote_id(remote_id)
                if chat:
                    self.deleteRemoteChat.emit(chat)
            else:
                self._add_remote_chat(remote_id)

    def _update_chat_filed(self, chat, key, value):
        match key:
            case 'model':
                chat.model = value
            case 'name':
                chat.name = value
            case 'saved_messages':
                chat.saved_messages = value
            case 'used_messages':
                chat.used_messages = value
            case 'temperature':
                chat.temperature = value
            case 'utime':
                chat.utime = value
            case 'type':
                chat.type = value
        self.updateChat.emit(chat)

    @asyncSlot()
    async def _add_remote_chat(self, remote_id):
        chat = self._database.get_by_remote_id(remote_id)
        data = await self._firebase.get(f'chats/{remote_id}')
        if chat is None:
            chat = self._database.add_chat()
            chat.remote_id = remote_id
            new_chat = True
        else:
            new_chat = False

        chat.model = data.get('model','default')
        chat.name = data.get('name', '')
        chat.saved_messages = data.get('saved_messages', 1000)
        chat.used_messages = data.get('used_messages', 1)
        chat.temperature = data.get('temperature', 0.5)
        chat.type = data.get('type', 0)
        chat.utime = data.get('utime', 0)

        if new_chat:
            self.newChat.emit(chat)
        else:
            self.updateChat.emit(chat)

    def _on_event(self, chat_id, events):
        if not chat_id or chat_id == 'None':
            return
        chat = self._database.get_by_remote_id(chat_id)
        to_add = []

        for el in sorted(events, key=lambda a: a[1]):
            type, index, data = el

            if type == 'last':
                pass
            elif index <= (chat.remote_last or -1):
                continue
            else:
                chat.remote_last = max(chat.remote_last or -1, index)
                if type == 'add':
                    to_add.append(data)
                elif type == 'delete':
                    if data in to_add:
                        to_add.remove(data)
                    else:
                        message = chat.get_message_by_remote_id(data)
                        if message is not None:
                            chat.delete_message(message.id)
                            self._database.commit()
                            self.deleteMessage.emit(chat.id, message)

        self._on_messages_add(chat, to_add)

    @asyncSlot()
    async def _on_messages_add(self, chat, message_remote_ids):
        for message_remote_id in message_remote_ids:
            data = await self._firebase.get(f'messages/{chat.remote_id}/{message_remote_id}')
            if data is None:
                continue

            reply = []
            for el in data.get('reply', []):
                mes = chat.get_message_by_remote_id(el)
                if mes:
                    reply.append(mes.id)
            message = chat.add_message(data['role'], data['content'], reply)
            message.replied_count = data.get('links', 1) - 1
            message.remote_id = message_remote_id
            self.newMessage.emit(chat.id, message)

    def new_chat(self):
        chat = self._database.add_chat()

        self.newChat.emit(chat)

    @asyncSlot()
    async def delete_chat(self, chat_id):
        chat = self._database.get_chat(chat_id)
        if chat is None:
            return

        try:
            await self.delete_remote_copy(chat)
        except aiohttp.ClientConnectionError:
            self.connectionErrorOccurred.emit()
            return

        for ext in ['.png', '.json']:
            path = os.path.join(self._sm.user_data_path, 'chat-icons', f'{chat.id}{ext}')
            if os.path.isfile(path):
                os.remove(path)
        chat.delete()
        self.deleteChat.emit(chat_id)

    async def update_chat_utime(self, chat: GPTChat):
        chat.utime = time.time()
        if chat.remote_id:
            await self._firebase.set(f'chats/{chat.remote_id}/utime', chat.utime)

    @asyncSlot()
    async def new_message(self, chat_id: int, role, content, reply: list | tuple = tuple()):
        chat = self._database.get_chat(chat_id)
        message = chat.add_message(role, content, reply)

        if chat.remote_id:
            try:
                message.remote_id = str(uuid4())
                chat.remote_last = (chat.remote_last or 0) + 1
                await self._firebase.set(f'messages/{chat.remote_id}/{message.remote_id}', message.to_dict())
                await self._firebase.set(f'events/{chat.remote_id}/{chat.remote_last}', ['add', message.remote_id])
                await self._firebase.set(f'events/{chat.remote_id}-last', chat.remote_last)
                for r_m in message.replys:
                    await self._firebase.set(f'messages/{chat.remote_id}/{r_m.remote_id}/links',
                                             r_m.replied_count + 1)
                await self.update_chat_utime(chat)
            except FirebaseError:
                self._database.rollback()
                return
            self._database.commit()

        self.newMessage.emit(chat_id, message)

    @asyncSlot()
    async def delete_message(self, chat_id, message):
        if message is None:
            return
        chat = self._database.get_chat(chat_id)

        if chat.remote_id:
            try:
                flag = await self._decrease_message_links(chat.remote_id, message.remote_id)
                if flag:
                    chat.remote_last += 1
                    await self._firebase.set(f'events/{chat.remote_id}/{chat.remote_last}', ['delete', message.remote_id])
                    await self._firebase.set(f'events/{chat.remote_id}-last', chat.remote_last)

                for mes in message.replys:
                    await self._decrease_message_links(chat.remote_id, mes.remote_id)

                await self.update_chat_utime(chat)

                chat.delete_message(message.id)
            except FirebaseError:
                self._database.rollback()
                return
        else:
            chat.delete_message(message.id)
        self._database.commit()

        self.deleteMessage.emit(chat_id, message)

    async def _decrease_message_links(self, chat_id, message_id):
        links = await self._firebase.get(f'messages/{chat_id}/{message_id}/links') - 1
        if links:
            await self._firebase.set(f'messages/{chat_id}/{message_id}/links', links)
            return False
        else:
            await self._firebase.delete(f'messages/{chat_id}/{message_id}')
            return True

    async def _update_chat_info(self, chat: GPTChat):
        await self._firebase.set(f'chats/{chat.remote_id}', {
            'id': chat.remote_id,
            'folder': chat.folder,
            'type_data': chat.type_data,
            'name': chat.name,
            'ctime': chat.ctime,
            'utime': chat.utime,
            'used_messages': chat.used_messages,
            'saved_messages': chat.saved_messages,
            'temperature': chat.temperature,
            'model': chat.model,
        })

    @asyncSlot()
    async def make_remote(self, chat: GPTChat, remote: bool):
        if remote == bool(chat.remote_id):
            if remote:
                try:
                    await self._update_chat_info(chat)
                except aiohttp.ClientConnectionError:
                    pass
            self._database.commit()

        elif not self._firebase.authorized:
            self._database.commit()

        elif remote:
            await self._push_chat(chat)

        else:
            await self.delete_remote_copy(chat)

    async def _push_chat(self, chat):
        try:
            chat.remote_id = str(uuid4())
            chat.remote_last = 0
            await self._update_chat_info(chat)
            for message in chat.messages:
                message.remote_id = str(uuid4())
                chat.remote_last += 1
                await self._firebase.set(f'events/{chat.remote_id}/{chat.remote_last}', ['add', message.remote_id])
                await self._firebase.set(f'messages/{chat.remote_id}/{message.remote_id}', message.to_dict())
            await self._firebase.set(f'events/{chat.remote_id}-last', chat.remote_last)
        except FirebaseError:
            self._database.rollback()
        else:
            self._database.commit()

    async def delete_remote_copy(self, chat: GPTChat):
        remote_id = chat.remote_id
        if not remote_id:
            return
        chat.remote_id = None
        self._database.commit()
        try:
            await self._firebase.delete(f'chats/{remote_id}')
            await self._firebase.delete(f'messages/{remote_id}')
            await self._firebase.delete(f'events/{remote_id}')
            await self._firebase.delete(f'events/{remote_id}-last')
        except FirebaseError:
            chat.remote_id = remote_id
            self._database.commit()
        except aiohttp.ClientConnectionError as ex:
            chat.remote_id = remote_id
            self._database.commit()
            raise ex

    def clear_model(self, model):
        for chat in self._database.chats:
            if chat.model == model:
                chat.model = 'default'
        self._database.commit()


class Looper(QThread):
    event = pyqtSignal(str, list)

    def __init__(self, fb: Firebase):
        super().__init__()
        self._firebase = fb
        self._stream = None

    def run(self) -> None:
        self._stream = self._firebase.stream('events', self.handler)

    def handler(self, event_dict):
        path = event_dict['path']
        data = event_dict['data']
        if data is None:
            return

        for key, item in (data.items() if path == '/' else [(path[1:], data)]):
            if key.endswith('-last'):
                key = key[:-len('-last')]
                self.event.emit(key, [['last', 0, item]])
            else:
                res = []
                for i, el in enumerate(item if isinstance(item, list) and isinstance(item[0], list) or item[0] is None else [item]):
                    if el:
                        if '/' in key:
                            i = int(key.split('/')[1])
                            key = key.split('/')[0]
                        if el[0] == 'add':
                            res.append(['add', i, el[1]])
                        else:
                            res.append(['delete', i, el[1]])
                self.event.emit(key, res)

    def terminate(self) -> None:
        self._stream.close()


class ChatsLooper(QThread):
    event = pyqtSignal(str, object)

    def __init__(self, fb: Firebase):
        super().__init__()
        self._firebase = fb
        self._stream = None

    def run(self) -> None:
        self._stream = self._firebase.stream('chats', self.handler)

    def handler(self, event_dict):
        path = event_dict['path']
        data = event_dict['data']
        self.event.emit(path, data)

    def terminate(self) -> None:
        self._stream.close()
