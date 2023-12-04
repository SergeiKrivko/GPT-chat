import json
import os.path
import time
from uuid import uuid4, UUID

from src.commands import write_file, read_json
from src.gpt.message import GPTMessage


class GPTChat:
    SIMPLE = 0
    TRANSLATE = 1
    SUMMARY = 2

    def __init__(self, path, chat_id=None):
        self._data_path = path

        if chat_id:
            self.id = UUID(chat_id)
        else:
            self.id = uuid4()

        self._path = f"{self._data_path}/{self.id}.json"

        self.messages: dict[UUID: GPTMessage] = dict()
        self.messages_order = []

        self.type = GPTChat.SIMPLE
        self.data = dict()

        self.name = ''
        self.time = 0
        self.utime = 0
        self.pinned = False
        self.used_messages = 10
        self.saved_messages = 100
        self.temperature = 0.5
        self.scrolling_pos = 0
        self.model = 'default'

    def store(self):
        write_file(self._path, json.dumps({
            'type': self.type,
            'data': self.data,
            'name': self.name,
            'messages': [self.messages[message_id].to_json() for message_id in self.messages_order],
            'time': self.time,
            'utime': self.utime,
            'pinned': self.pinned,
            'model': self.model,
            'used_messages': self.used_messages,
            'saved_messages': self.saved_messages,
            'temperature': self.temperature,
            'scrolling_pos': self.scrolling_pos
        }, ensure_ascii=False))

    def load(self):
        data = read_json(self._path)
        self.type = data.get('type', GPTChat.SIMPLE)
        self.data = data.get('data', dict())
        self.name = data.get('name', '')
        self.time = data.get('time', 0)
        self.utime = data.get('utime', 0)
        self.pinned = data.get('pinned', False)

        for el in data.get('messages', []):
            self.append_message(el['role'], el['content'])

        self.model = data.get('model', 'default')
        self.used_messages = data.get('used_messages', 0)
        self.saved_messages = data.get('saved_messages', 0)
        self.temperature = data.get('temperature', 0)
        self.scrolling_pos = data.get('scrolling_pos', 0)

    def get_sort_key(self):
        res = self.utime
        if res <= 0:
            res = self.time
        if self.pinned:
            res += 10000000000
        return res

    def set_name(self, name):
        self.name = name
        self.store()

    def set_time(self, time):
        self.time = time
        self.store()

    def set_pinned(self, flag):
        self.pinned = flag
        self.store()

    @property
    def last_message(self):
        return self.messages[self.messages_order[-1]]

    def messages_to_prompt(self, reply: list[UUID] = tuple()):
        ind = min(len(self.messages), self.used_messages)
        ids = self.messages_order[-ind:]
        for el in reversed(reply):
            if el not in ids:
                ids.insert(0, el)

        return self.system_prompts() + [self.messages[message_id].to_json() for message_id in ids]

    def append_message(self, role, content, reply=tuple()):
        message = GPTMessage(role, content, reply)
        self.messages[message.id] = message
        self.messages_order.append(message.id)
        while len(self.messages) > self.saved_messages:
            self.messages.pop(0)
        self.utime = time.time()
        self.store()
        return message

    def pop_message(self, message_id):
        self.messages_order.remove(message_id)
        res = self.messages.pop(message_id)
        self.store()
        return res

    def delete(self):
        if os.path.isfile(self._path):
            os.remove(self._path)

    def system_prompts(self):
        match self.type:
            case GPTChat.SIMPLE:
                return []
            case GPTChat.TRANSLATE:
                return [{'role': 'system', 'content': f"You translate messages from {self.data['language1']} to "
                                                      f"{self.data['language2']} or vice versa. ONLY TRANSLATE!"}]
            case GPTChat.SUMMARY:
                return [{'role': 'system', 'content': "You compose a summary of the messages sent to you using"
                                                      " russian language"}]
