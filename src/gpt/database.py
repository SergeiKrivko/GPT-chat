import os
import shutil
import sqlite3
from time import time

from src.commands import read_json
from src.gpt import chat
from src.gpt.firebase import Firebase
from src.settings_manager import SettingsManager


class Database:
    def __init__(self, sm: SettingsManager):
        self._sm = sm
        self._dir = ""
        self.firebase = Firebase('', '')
        self._connection = None
        self.cursor: sqlite3.Cursor
        self.update_user()

    def update_user(self):
        if isinstance(self._connection, sqlite3.Connection):
            self._connection.close()

        if self._dir.endswith('default_user') and not os.path.isdir(self._sm.user_data_path):
            os.makedirs(self._sm.user_data_path)
            shutil.copyfile(f"{self._dir}/database.db", f"{self._sm.user_data_path}/database.db")

        self._dir = self._sm.user_data_path
        os.makedirs(self._dir, exist_ok=True)
        self._connection = sqlite3.connect(f"{self._dir}/database.db")
        self.firebase.set_user(self._sm.get('user_id'), self._sm.get('user_token'))

        self.cursor = self._connection.cursor()

        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS Chats (
        id INTEGER PRIMARY KEY,
        type INTEGER NOT NULL,
        type_data TEXT,
        remote_id TEXT,
        remote_last INTEGER,
        chat_name TEXT,
        ctime REAL NOT NULL,
        utime REAL NOT NULL,
        pinned INTEGER NOT NULL,
        used_messages INTEGER NOT NULL,
        saved_messages INTEGER NOT NULL,
        temperature REAL NOT NULL,
        model TEXT NOT NULL,
        scrolling_pos INTEGER
        )''')

        for chat_id in self.chat_ids:
            self._create_chat_table(chat_id)

        self._connection.commit()

    def _create_chat_table(self, chat_id):
        self.cursor.execute(f'''
                            CREATE TABLE IF NOT EXISTS Messages{chat_id} (
                            id INTEGER PRIMARY KEY,
                            remote_id TEXT,
                            role TEXT,
                            content TEXT,
                            replys BLOB,
                            replied_count INTEGER,
                            deleted INTEGER NOT NULL,
                            ctime REAL
                            )''')

    @property
    def chat_ids(self):
        self.cursor.execute('SELECT id FROM Chats')
        chats = self.cursor.fetchall()
        for el in chats:
            yield el[0]

    @property
    def chats(self):
        for el in self.chat_ids:
            yield chat.GPTChat(self, self._sm, el)

    async def get_remote_deleted_chats(self):
        chats = await self.firebase.get_chats()
        for chat in self.chats:
            if chat.remote_id and chat.remote_id not in chats:
                yield chat.id

    async def load_remote(self):
        chats = await self.firebase.get_chats()
        for remote_id in chats:
            self.cursor.execute(f'SELECT id FROM Chats WHERE remote_id = "{remote_id}"')
            if not self.cursor.fetchone():
                res = self.add_chat()
                res.remote_id = remote_id
                await self.firebase.download_chat(res)
                self._connection.commit()
                yield res

    def add_chat(self):
        self.cursor.execute(f"""INSERT INTO Chats (
        type, ctime, utime, pinned, used_messages, saved_messages, temperature, model, scrolling_pos, remote_id) 
        VALUES ({chat.GPTChat.SIMPLE}, {time()}, {time()}, 0, 1, 1000, 0.5, "default", 0, NULL)""")
        chat_id = self.cursor.lastrowid
        self._create_chat_table(chat_id)
        self._connection.commit()
        return chat.GPTChat(self, self._sm, chat_id)

    def from_json_file(self, path):
        data = read_json(path)
        new_chat = self.add_chat()

        new_chat.name = data.get('name')
        new_chat.type = data.get('type')
        new_chat.type_data = data.get('data')
        new_chat.model = data.get('model', 'default')
        new_chat.ctime = data.get('time')
        new_chat.utime = data.get('utime')
        new_chat.pinned = data.get('pinned', False)
        new_chat.used_messages = data.get('used_messages')
        new_chat.saved_messages = data.get('saved_messages')
        new_chat.temperature = data.get('temperature')
        for message in data.get('messages'):
            new_chat.add_message(message['role'], message['content'])

    def commit(self):
        self._connection.commit()

    def __del__(self):
        self._connection.commit()
        self._connection.close()
