import json
import os.path
import platform
import sys
import zipfile
from urllib.parse import quote

import requests

from src import config


token = ""


def auth():
    rest_api_url = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
    r = requests.post(rest_api_url,
                      params={"key": config.FIREBASE_API_KEY},
                      data=json.dumps({"email": os.getenv("AdminEmail"),
                                       "password": os.getenv("AdminPassword"),
                                       "returnSecureToken": True}))
    if not r.ok:
        raise Exception("Can not authorized")
    res = r.json()
    global token
    token = res['idToken']


def upload_file(path, name=''):
    if name and '.' not in name:
        name += '.' + path.split('.')[-1]
    url = f"https://firebasestorage.googleapis.com/v0/b/gpt-chat-bf384.appspot.com/o/" \
          f"{quote(f'releases/{name or os.path.basename(path)}', safe='')}{f'?auth={token}' if token else ''}"
    with open(path, 'br') as f:
        resp = requests.post(url, data=f.read())
        if not resp.ok:
            raise Exception(resp.text)


def download_file(name):
    url = f"https://firebasestorage.googleapis.com/v0/b/gpt-chat-bf384.appspot.com/o/" \
          f"{quote(f'releases/{name}', safe='')}?alt=media{f'?auth={token}' if token else ''}"
    resp = requests.get(url, stream=True)
    if resp.ok:
        return b''.join(resp).decode('utf-8')
    else:
        return ''


def get_system():
    match sys.platform:
        case 'win32':
            return 'windows'
        case 'linux':
            return 'linux'
        case 'darwin':
            return 'macos'


def get_arch():
    return os.getenv('ARCHITECTURE')


def release_file():
    match sys.platform:
        case 'win32':
            return r"dist\GPT-chat_setup.exe"
        case 'linux':
            return f"gptchat_{config.APP_VERSION}_amd64.deb"
        case 'darwin':
            return "GPT-chat.dmg"


def version_file():
    return f"{get_system()}-{get_arch()}.json"


def upload_version(name=None):
    url = f"https://firebasestorage.googleapis.com/v0/b/gpt-chat-bf384.appspot.com/o/" \
          f"{quote(f'releases/{name or version_file()}', safe='')}{f'?auth={token}' if token else ''}"
    resp = requests.post(url, data=json.dumps({
        'version': config.APP_VERSION,
        'size': os.path.getsize(release_file()),
    }, indent=2).encode('utf-8'))
    if not resp.ok:
        raise Exception(resp.text)


def compress_to_zip(path):
    archive = zipfile.ZipFile(path + '.zip', 'w')
    archive.write(path, os.path.basename(path))
    archive.close()
    return path + '.zip'


def main():
    # auth()
    upload_file(compress_to_zip(release_file()), f"{get_system()}-{get_arch()}.zip")
    upload_version()
    if get_arch() == 'x86-64':
        upload_file(release_file(), f"{get_system()}.zip")
        upload_version(f"{get_system()}.json")


if __name__ == '__main__':
    main()
