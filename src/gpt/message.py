from typing import Literal
from uuid import uuid4


class GPTMessage:
    def __init__(self, role: Literal['user', 'assistant', 'system'], content: str):
        self.id = uuid4()
        self.role = role
        self.content = content

    def to_json(self):
        return {'role': self.role, 'content': self.content}
