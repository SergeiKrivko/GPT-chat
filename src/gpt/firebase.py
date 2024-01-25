import json
from uuid import uuid4

import aiohttp

import src.gpt.message as gpt_message
import src.gpt.chat as gpt_chat


class FirebaseError(Exception):
    def __init__(self, *args):
        self.message = args[0]

    def __str__(self):
        return self.message


class Firebase:
    def __init__(self, user_id, user_token):
        self._user_id = user_id
        self._user_token = user_token

    def set_user(self, user_id, user_token):
        self._user_id = user_id
        self._user_token = user_token

    def _url(self, key):
        return f"https://gpt-chat-bf384-default-rtdb.europe-west1.firebasedatabase.app/users/" \
               f"{self._user_id}/{key}.json?auth={self._user_token}"

    async def _get(self, key: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(self._url(key)) as resp:
                res = await resp.text()
                if not resp.ok:
                    raise FirebaseError(res)
        return json.loads(res)

    async def _select(self, key, start=None, end=None):
        url = self._url(key) + '&orderBy="$key"'
        if start is not None:
            url += f'&startAt="{str(start)}"'
        if end is not None:
            url += f'&endAt="{str(end)}"'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                res = await resp.text()
                if not resp.ok:
                    raise FirebaseError(res)
        res = json.loads(res)
        if res is None:
            res = dict()
        return res

    async def _set(self, key: str, value):
        async with aiohttp.ClientSession() as session:
            async with session.put(self._url(key), data=json.dumps(value)) as resp:
                res = await resp.text()
                if not resp.ok:
                    raise FirebaseError(res)
        return res

    async def _delete(self, key):
        async with aiohttp.ClientSession() as session:
            async with session.delete(self._url(key)) as resp:
                res = await resp.text()
                if not resp.ok:
                    raise FirebaseError(res)
        return res

    async def update_chat(self, chat):
        if chat.remote_id is None:
            chat.remote_id = str(uuid4())
        await self._set(f'chats/{chat.remote_id}', {
            'id': chat.remote_id,
            'type': chat.type,
            'type_data': chat.type_data,
            'name': chat.name,
            'ctime': chat.ctime,
            'utime': chat.utime,
            'used_messages': chat.used_messages,
            'saved_messages': chat.saved_messages,
            'temperature': chat.temperature,
            'model': chat.model,
        })

    async def delete_chat(self, chat):
        try:
            await self._delete(f'chats/{chat.remote_id}')
        except FirebaseError:
            pass
        try:
            await self._delete(f'messages/{chat.remote_id}')
        except FirebaseError:
            pass
        try:
            await self._delete(f'events/{chat.remote_id}')
        except FirebaseError:
            pass
        try:
            await self._delete(f'events/{chat.remote_id}-last')
        except FirebaseError:
            pass

    async def _add_message(self, chat, message):
        message.remote_id = str(uuid4())
        await self._set(f'messages/{chat.remote_id}/{message.remote_id}', {
            'id': message.remote_id,
            'content': message.content,
            'role': message.role,
            'ctime': message.ctime,
            'replys': [m.remote_id for m in message.replys],
            'replied_count': message.replied_count,
        })

    async def get_message(self, chat, remote_id):
        if not isinstance(chat, gpt_chat.GPTChat):
            return
        data = await self._get(f'messages/{chat.remote_id}/{remote_id}')
        message = chat.add_message(data.get('role'), data.get('content'), skip_event=True)
        message.remote_id = remote_id
        message.ctime = data.get('ctime')
        return message

    async def add_events(self, chat, events: list):
        if not events:
            return
        event_id = await self._get(f'events/{chat.remote_id}-last')
        if not event_id:
            event_id = 0
        for event in events:
            event_id += 1
            if event[0] == 'add':
                await self._add_message(chat, chat.get_message(event[1]))
                await self._set(f'events/{chat.remote_id}/{event_id}', [event[0], chat.get_message(event[1]).remote_id])
            else:
                await self._set(f'events/{chat.remote_id}/{event_id}', event)
        await self._set(f'events/{chat.remote_id}-last', event_id)
        chat.remote_last = event_id

    async def get_events(self, chat):
        start = chat.remote_last
        if isinstance(start, int):
            start += 1
        else:
            start = 1
        events = await self._select(f'events/{chat.remote_id}', start=start)
        messages = []
        for ind in sorted(events, key=int):
            event = events[ind]
            if event and event[0] == 'add':
                message = await self.get_message(chat, event[1])
                messages.append(message)
            elif event and event[0] == 'delete':
                chat.delete_by_remote_id(event[1])
        chat.remote_last = start + len(events) - 1
        return messages

    async def upload_chat(self, chat):
        await self.update_chat(chat)
        await self.add_events(chat, [('add', m.id) for m in chat.messages])

    async def download_chat(self, chat):
        if not isinstance(chat, gpt_chat.GPTChat):
            return
        data = await self._get(f'chats/{chat.remote_id}')
        chat.name = data.get('name')
        chat.used_messages = data.get('used_messages')
        chat.saved_messages = data.get('saved_messages')
        chat.temperature = data.get('temperature')
        chat.utime = data.get('utime')
        await self.get_events(chat)

    async def get_chats(self):
        res = await self._get('chats')
        if not res:
            return []
        return list(res.keys())
