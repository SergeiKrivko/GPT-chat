import os
import shutil
import sqlite3
from time import time

from src.gpt import chat
from src.settings_manager import SettingsManager


class Database:
    def __init__(self, sm: SettingsManager):
        self._sm = sm
        self._dir = ""
        self._connection = None
        self.cursor: sqlite3.Cursor
        self.update_user()

        self.firebase = None

    def update_user(self):
        if isinstance(self._connection, sqlite3.Connection):
            self._connection.close()

        if self._dir.endswith('default_user') and not os.path.isdir(self._sm.user_data_path):
            os.makedirs(self._sm.user_data_path)
            shutil.copyfile(f"{self._dir}/database.db", f"{self._sm.user_data_path}/database.db")

        self._dir = self._sm.user_data_path
        os.makedirs(self._dir, exist_ok=True)
        self._connection = sqlite3.connect(f"{self._dir}/database.db")

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

    def add_chat(self):
        self.cursor.execute(f"""INSERT INTO Chats (
        type, ctime, utime, pinned, used_messages, saved_messages, temperature, model, scrolling_pos, remote_id) 
        VALUES ({chat.GPTChat.SIMPLE}, {time()}, {time()}, 0, 1, 1000, 0.5, "default", 0, NULL)""")
        chat_id = self.cursor.lastrowid
        self._create_chat_table(chat_id)
        self._connection.commit()
        return chat.GPTChat(self, self._sm, chat_id)

    def get_chat(self, chat_id):
        self.cursor.execute('SELECT id FROM Chats WHERE id = ?', (chat_id,))
        res = self.cursor.fetchone()
        if res is None:
            return res
        return chat.GPTChat(self, self._sm, res[0])

    def get_by_remote_id(self, remote_id):
        self.cursor.execute('SELECT id FROM Chats WHERE remote_id = ?', (remote_id,))
        res = self.cursor.fetchone()
        if res is None:
            return res
        return chat.GPTChat(self, self._sm, res[0])

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def __del__(self):
        self._connection.commit()
        self._connection.close()
