import asyncio
import json
import re
import socket
import threading
import time
import warnings

import aiohttp
import requests
from requests import Session

from src import config


class FirebaseError(Exception):
    def __init__(self, *args):
        self.message = args[0]

    def __str__(self):
        return self.message


class Firebase:
    def __init__(self, sm):
        self._sm = sm
        self._user_id = ""
        self._user_token = ""
        self._authorized = False

        self._session = aiohttp.ClientSession()

        self.expires_in = 0

    @property
    def authorized(self):
        return self._authorized

    async def auth(self):
        self._user_id = self._sm.get('user_id')
        self._user_token = self._sm.get('user_token')
        self._authorized = False
        if self._user_id:
            await self._auth()

    async def _auth(self):
        try:
            async with self._session.post(
                    f"https://securetoken.googleapis.com/v1/token?key={config.FIREBASE_API_KEY}",
                    data={
                        'grant_type': 'refresh_token',
                        'refresh_token': self._sm.get('user_refresh_token')
                    }) as resp:
                if resp.ok:
                    res = await resp.json()
                    self._authorized = True
                    self._user_token = res['access_token']
                    self._sm.set('user_token', res['access_token'])
                    self._sm.set('user_refresh_token', res['refresh_token'])
                    self.expires_in = int(res['expires_in'])

                else:
                    self._authorized = False
                    self._sm.set('user_token', '')

        except aiohttp.ClientConnectionError:
            self._authorized = False

    def _url(self, key):
        return f"https://gpt-chat-bf384-default-rtdb.europe-west1.firebasedatabase.app/users/" \
               f"{self._user_id}/{key}.json?auth={self._user_token}"

    async def get(self, key: str):
        async with self._session.get(self._url(key)) as resp:
            res = await resp.text()
            if not resp.ok:
                raise FirebaseError(res)
        return json.loads(res)

    async def select(self, key, start=None, end=None):
        url = self._url(key) + '&orderBy="$key"'
        if start is not None:
            url += f'&startAt="{str(start)}"'
        if end is not None:
            url += f'&endAt="{str(end)}"'
        async with self._session.get(url) as resp:
            res = await resp.text()
            if not resp.ok:
                raise FirebaseError(res)
        return json.loads(res)

    async def set(self, key: str, value):
        async with self._session.put(self._url(key), data=json.dumps(value)) as resp:
            res = await resp.text()
            if not resp.ok:
                raise FirebaseError(res)
        return res

    async def delete(self, key):
        async with self._session.delete(self._url(key)) as resp:
            res = await resp.text()
            if not resp.ok:
                raise FirebaseError(res)
        return res

    def stream(self, key, handler):
        return Stream(self._url(key), handler, build_headers, None, True)


def build_headers(token=None):
    headers = {"content-type": "application/json; charset=UTF-8"}
    return headers


end_of_field = re.compile(r'\r\n\r\n|\r\r|\n\n')


class SSEClient(object):
    def __init__(self, url, session, build_headers, last_id=None, retry=3000, **kwargs):
        self.url = url
        self.last_id = last_id
        self.retry = retry
        self.running = True
        # Optional support for passing in a requests.Session()
        self.session = session
        # function for building auth header when token expires
        self.build_headers = build_headers
        self.start_time = None
        # Any extra kwargs will be fed into the requests.get call later.
        self.requests_kwargs = kwargs

        # The SSE spec requires making requests with Cache-Control: nocache
        if 'headers' not in self.requests_kwargs:
            self.requests_kwargs['headers'] = {}
        self.requests_kwargs['headers']['Cache-Control'] = 'no-cache'

        # The 'Accept' header is not required, but explicit > implicit
        self.requests_kwargs['headers']['Accept'] = 'text/event-stream'

        # Keep data here as it streams in
        self.buf = u''

        self._connect()

    def _connect(self):
        if self.last_id:
            self.requests_kwargs['headers']['Last-Event-ID'] = self.last_id
        headers = self.build_headers()
        self.requests_kwargs['headers'].update(headers)
        # Use session if set.  Otherwise fall back to requests module.
        self.requester = self.session or requests
        self.resp = self.requester.get(self.url, stream=True, **self.requests_kwargs)

        self.resp_iterator = self.resp.iter_content(decode_unicode=True)

        # attribute on Events like the Javascript spec requires.
        self.resp.raise_for_status()

    def _event_complete(self):
        return re.search(end_of_field, self.buf) is not None

    def __iter__(self):
        return self

    def __next__(self):
        while not self._event_complete():
            try:
                nextchar = next(self.resp_iterator)
                self.buf += nextchar
            except (StopIteration, requests.RequestException):
                time.sleep(self.retry / 1000.0)
                self._connect()

                # The SSE spec only supports resuming from a whole message, so
                # if we have half a message we should throw it out.
                head, sep, tail = self.buf.rpartition('\n')
                self.buf = head + sep
                continue

        split = re.split(end_of_field, self.buf)
        head = split[0]
        tail = "".join(split[1:])

        self.buf = tail
        msg = Event.parse(head)

        if msg.data == "credential is no longer valid":
            self._connect()
            return None

        if msg.data == 'null':
            return None

        # If the server requests a specific retry delay, we need to honor it.
        if msg.retry:
            self.retry = msg.retry

        # last_id should only be set if included in the message.  It's not
        # forgotten if a message omits it.
        if msg.id:
            self.last_id = msg.id

        return msg


class Event(object):

    sse_line_pattern = re.compile('(?P<name>[^:]*):?( ?(?P<value>.*))?')

    def __init__(self, data='', event='message', id=None, retry=None):
        self.data = data
        self.event = event
        self.id = id
        self.retry = retry

    def dump(self):
        lines = []
        if self.id:
            lines.append('id: %s' % self.id)

        # Only include an event line if it's not the default already.
        if self.event != 'message':
            lines.append('event: %s' % self.event)

        if self.retry:
            lines.append('retry: %s' % self.retry)

        lines.extend('data: %s' % d for d in self.data.split('\n'))
        return '\n'.join(lines) + '\n\n'

    @classmethod
    def parse(cls, raw):
        """
        Given a possibly-multiline string representing an SSE message, parse it
        and return a Event object.
        """
        msg = cls()
        for line in raw.split('\n'):
            m = cls.sse_line_pattern.match(line)
            if m is None:
                # Malformed line.  Discard but warn.
                warnings.warn('Invalid SSE line: "%s"' % line, SyntaxWarning)
                continue

            name = m.groupdict()['name']
            value = m.groupdict()['value']
            if name == '':
                # line began with a ":", so is a comment.  Ignore
                continue

            if name == 'data':
                # If we already have some data, then join to it with a newline.
                # Else this is it.
                if msg.data:
                    msg.data = '%s\n%s' % (msg.data, value)
                else:
                    msg.data = value
            elif name == 'event':
                msg.event = value
            elif name == 'id':
                msg.id = value
            elif name == 'retry':
                msg.retry = int(value)

        return msg

    def __str__(self):
        return self.data


class ClosableSSEClient(SSEClient):
    def __init__(self, *args, **kwargs):
        self.should_connect = True
        super(ClosableSSEClient, self).__init__(*args, **kwargs)

    def _connect(self):
        if self.should_connect:
            super(ClosableSSEClient, self)._connect()
        else:
            raise StopIteration()

    def close(self):
        self.should_connect = False
        self.retry = 0
        self.resp.raw._fp.fp.raw._sock.shutdown(socket.SHUT_RDWR)
        self.resp.raw._fp.fp.raw._sock.close()


class Stream:
    def __init__(self, url, stream_handler, build_headers, stream_id, is_async):
        self.build_headers = build_headers
        self.url = url
        self.stream_handler = stream_handler
        self.stream_id = stream_id
        self.sse = None
        self.thread = None

        if is_async:
            self.start()
        else:
            self.start_stream()

    def make_session(self):
        """
        Return a custom session object to be passed to the ClosableSSEClient.
        """
        session = KeepAuthSession()
        return session

    def start(self):
        self.thread = threading.Thread(target=self.start_stream)
        self.thread.start()
        return self

    def start_stream(self):
        self.sse = ClosableSSEClient(self.url, session=self.make_session(), build_headers=self.build_headers)
        for msg in self.sse:
            if msg:
                msg_data = json.loads(msg.data)
                msg_data["event"] = msg.event
                if self.stream_id:
                    msg_data["stream_id"] = self.stream_id
                self.stream_handler(msg_data)

    def close(self):
        while not self.sse and not hasattr(self.sse, 'resp'):
            time.sleep(0.001)
        self.sse.running = False
        self.sse.close()
        self.thread.join()
        return self


class KeepAuthSession(Session):
    """
    A session that doesn't drop Authentication on redirects between domains.
    """

    def rebuild_auth(self, prepared_request, response):
        pass
