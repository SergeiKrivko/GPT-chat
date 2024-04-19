import importlib
import json
import os.path
import sys


class Plugin:
    def __init__(self, path):
        self._path = path

        config_file = os.path.join(path, 'gptchat-provider-config.json')

        with open(config_file, encoding='utf-8') as f:
            plugin_config = json.load(f)

        self._name = plugin_config.get('name', '')
        self._model_name = plugin_config.get('model_name', f'Custom ({self._name})')
        self._description = plugin_config.get('description', '')
        self._module = plugin_config.get('module', 'main')
        self._function_name = plugin_config.get('function', 'main')
        self._version = plugin_config.get('version', '0.1.0')

        self._function = self._import()

    def _import(self):
        sys.path.insert(0, self._path)
        plugin_module = importlib.import_module(self._module)
        sys.path.pop(0)
        return getattr(plugin_module, self._function_name)

    def __call__(self, messages: list[dict[str: str]], **kwargs):
        return self._function(messages, **kwargs)

    def call(self, messages: list[dict[str: str]], **kwargs):
        return self._function(messages, **kwargs)

    @property
    def name(self):
        return self._name

    @property
    def model_name(self):
        return self._model_name

    @property
    def description(self):
        return self._description

    @property
    def version(self):
        return self._version

