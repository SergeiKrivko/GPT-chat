import asyncio
import sys

from src import config
from src.commands import read_json
from src.macos_sert import sert


def main():
    parse_args(sys.argv)


def parse_args(args: list[str]):
    i = 1

    if '--test' in args:
        config.APP_NAME += '-test'

    messages = []
    model = ''

    while i < len(args):
        arg = args[i]
        if arg in ['-v', '--version']:
            print(f"GPT-chat, version {config.APP_VERSION}")
            return
        elif arg in ['-h', '--help']:
            print(f"""GPT-chat, version {config.APP_VERSION}

Использование: GPT-chat [options]
При запуске без аргументов открывает приложение
При запуске с одним аргументом отправляет сообщение и печатает ответ

Опции:
    -m, --message MESSAGE       Отправляет сообщение и печатает ответ в консоль. 
                                Может быть использован несколько раз, чтобы передать несколько сообщений одним запросом.
    -j, --json FILE             Отправляет сообщения из файла. Можно использовать несколько раз, в том числе в сочетании
                                с --message
    -v, --version               Печатает текущую версию программы
    -h, --help                  Печатает это сообщение
""")
            return
        elif arg in ['-j', '--json'] and i + 1 < len(args):
            path = args[i + 1]
            messages.extend(read_json(path, list))
            i += 1
        elif arg in ['-m', '--message'] and i + 1 < len(args):
            messages.append({'role': 'user', 'content': args[i + 1]})
            i += 1
        elif arg in ['--model'] and i + 1 < len(args):
            model = args[i + 1]
            i += 1
        elif len(args) == 2:
            messages.append({'role': 'user', 'content': arg})
        else:
            print(f"Invalid argument: {arg}")
            return
        i += 1

    # if messages:
    #     import src.gpt as gpt
    #     for el in gpt.stream_response(messages):
    #         print(el, end='')
    #     print()
    # else:
    run_app()


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


def run_app():
    from qasync import QEventLoop, QApplication

    from src.ui.main_window import MainWindow

    sert()

    app = QApplication([])
    app.setOrganizationName(config.ORGANISATION_NAME)
    app.setOrganizationDomain(config.ORGANISATION_URL)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(config.APP_VERSION)

    event_loop = QEventLoop(app)
    asyncio.set_event_loop(event_loop)

    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)

    window = MainWindow(app)
    window.show()
    # window.set_theme()
    sys.excepthook = except_hook

    with event_loop:
        event_loop.run_until_complete(app_close_event.wait())


if __name__ == '__main__':
    main()
