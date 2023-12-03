from typing import Literal
from uuid import uuid4


class GPTMessage:
    def __init__(self, role: Literal['user', 'assistant', 'system'], content: str):
        self._id = uuid4()
        self.role = role
        self.content = content

    @property
    def id(self):
        return self._id

    def to_json(self):
        return {'role': self.role, 'content': self.content}
