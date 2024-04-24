import json
import os.path

from g4f.client import Client

from src.gpt.plugins import Plugin

global g4f


plugins = dict()

inited = False


def init(sm):
    from time import sleep

    sleep(3)
    global g4f
    import g4f as lib
    g4f = lib

    for el in json.loads(sm.get('plugins', '[]')):
        plugin = Plugin(os.path.join(sm.app_data_dir, 'plugins', el))
        plugins[plugin.name] = plugin
        sleep(0.1)

    global inited
    inited = True


def stream_response(messages: list[dict[str: str]], model=None, **kwargs):
    if model is None or model == 'default':
        model = g4f.models.default

    elif model.startswith('__plugin_'):
        for el in plugins[model[9:]](messages, **kwargs):
            yield el
        return

    try:
        response = g4f.ChatCompletion.create(
            model=model,
            messages=messages,
            timeout=120,
            stream=True,
            **kwargs
        )
        for el in response:
            yield el
    except g4f.StreamNotSupportedError:
        yield simple_response(messages, model, **kwargs)


def simple_response(messages: list[dict[str: str]], model=None, **kwargs):
    if model is None or model == 'default':
        model = g4f.models.default

    if model.startswith('__plugin_'):
        return ''.join(plugins[model[9:]](messages, **kwargs))

    response = g4f.ChatCompletion.create(
        model=model,
        messages=messages,
        timeout=120,
        **kwargs
    )
    return response


def try_response(messages: list[dict[str: str]], model=None, count=5, handler=None, **kwargs):
    if model is None or model == 'default':
        model = g4f.models.default
    for _ in range(count):
        try:
            response = g4f.ChatCompletion.create(
                model=model,
                messages=messages,
                timeout=120,
                **kwargs
            )
            if handler is None:
                return response
            return handler(response)
        except RuntimeError:
            pass
    return ''


def get_models():
    yield 'default'
    try:
        for el in g4f.models._all_models:
            yield el
    except NameError:
        pass
    for plugin in plugins.keys():
        yield f'__plugin_{plugin}'
