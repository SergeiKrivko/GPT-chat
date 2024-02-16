import json
import os.path
import sys
import zipfile
from urllib.parse import quote

import requests

from src import config


def upload_file(path, name=''):
    if name and '.' not in name:
        name += '.' + path.split('.')[-1]
    url = f"https://firebasestorage.googleapis.com/v0/b/gpt-chat-bf384.appspot.com/o/" \
          f"{quote(f'releases/{name or os.path.basename(path)}', safe='')}"
    with open(path, 'br') as f:
        resp = requests.post(url, data=f.read())
        if not resp.ok:
            raise Exception(resp.text)


def download_file(name):
    url = f"https://firebasestorage.googleapis.com/v0/b/gpt-chat-bf384.appspot.com/o/" \
          f"{quote(f'releases/{name}', safe='')}?alt=media"
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


def release_file():
    match sys.platform:
        case 'win32':
            return r"dist\GPT-chat_setup.exe"
        case 'linux':
            return f"gptchat_{config.APP_VERSION}_amd64.deb"
        case 'darwin':
            return "GPT-chat_macos.dmg"


def version_file():
    return f"{get_system()}.json"


def upload_version():
    url = f"https://firebasestorage.googleapis.com/v0/b/gpt-chat-bf384.appspot.com/o/" \
          f"{quote(f'releases/{version_file()}', safe='')}"
    resp = requests.post(url, data=json.dumps({
        'version': config.APP_VERSION,
    }, indent=2).encode('utf-8'))
    if not resp.ok:
        raise Exception(resp.text)


def compress_to_zip(path):
    archive = zipfile.ZipFile(path + '.zip', 'w')
    archive.write(path, get_system() + '.' + path.split('.')[-1])
    archive.close()
    return path + '.zip'


def main():
    upload_file(compress_to_zip(release_file()), get_system())
    upload_version()


if __name__ == '__main__':
    main()
