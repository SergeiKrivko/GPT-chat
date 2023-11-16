import json
import os.path
import time
from uuid import uuid4, UUID

from src.commands import write_file, read_json


class GPTDialog:
    SIMPLE = 0
    TRANSLATE = 1
    SUMMARY = 2

    def __init__(self, path, dialog_id=None):
        self._data_path = path

        if dialog_id:
            self.id = UUID(dialog_id)
        else:
            self.id = uuid4()

        self._path = f"{self._data_path}/{self.id}.json"

        self.messages = []
        self.type = GPTDialog.SIMPLE
        self.data = dict()
        self.name = ''
        self.time = 0
        self.utime = 0
        self.used_messages = 10
        self.saved_messages = 100
        self.temperature = 0.5
        self.scrolling_pos = 0

    def store(self):
        write_file(self._path, json.dumps({
            'type': self.type,
            'data': self.data,
            'name': self.name,
            'messages': self.messages,
            'time': self.time,
            'utime': self.utime,
            'used_messages': self.used_messages,
            'saved_messages': self.saved_messages,
            'temperature': self.temperature,
            'scrolling_pos': self.scrolling_pos
        }, ensure_ascii=False))

    def load(self):
        data = read_json(self._path)
        self.type = data.get('type', GPTDialog.SIMPLE)
        self.data = data.get('data', dict())
        self.name = data.get('name', '')
        self.time = data.get('time', 0)
        self.utime = data.get('utime', 0)
        self.messages = data.get('messages', [])
        self.used_messages = data.get('used_messages', 0)
        self.saved_messages = data.get('saved_messages', 0)
        self.temperature = data.get('temperature', 0)
        self.scrolling_pos = data.get('scrolling_pos', 0)

    def set_name(self, name):
        self.name = name
        self.store()

    def set_time(self, time):
        self.time = time
        self.store()

    def append_message(self, role, content):
        message = {'role': role, 'content': content}
        self.messages.append(message)
        while len(self.messages) > self.saved_messages:
            self.messages.pop(0)
        self.utime = time.time()
        self.store()
        return message

    def pop_message(self, index):
        res = self.messages.pop(index)
        self.store()
        return res

    def delete(self):
        if os.path.isfile(self._path):
            os.remove(self._path)

    def system_prompts(self):
        match self.type:
            case GPTDialog.SIMPLE:
                return []
            case GPTDialog.TRANSLATE:
                return [{'role': 'system', 'content': f"You translate messages from {self.data['language1']} to "
                                                      f"{self.data['language2']} or vice versa"}]
            case GPTDialog.SUMMARY:
                return [{'role': 'system', 'content': "you compose a summary of the messages sent to you"}]
