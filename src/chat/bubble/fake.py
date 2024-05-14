from src.chat.bubble import ChatBubble


class _FakeMessage:
    def __init__(self):
        self._content = ''

    @property
    def content(self):
        return self._content

    @content.setter
    def content(self, value):
        self._content = value

    def add_text(self, text):
        self._content += text

    @property
    def replys(self):
        return []

    @property
    def role(self):
        return 'assistant'

    @property
    def id(self):
        return -1


class FakeBubble(ChatBubble):
    def __init__(self, sm, chat):
        super().__init__(sm, chat, _FakeMessage())

    def clear_content(self):
        super().clear_content()
        self.message.content = ''
