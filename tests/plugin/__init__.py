# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

import quodlibet
from quodlibet import util
from quodlibet.util import get_module_dir
from quodlibet.util.modulescanner import ModuleScanner
from quodlibet.plugins import list_plugins, Plugin, PluginImportError

from tests import TestCase, init_fake_app, destroy_fake_app


init_fake_app, destroy_fake_app  # noqa

# Nasty hack to allow importing of plugins...
PLUGIN_DIRS = []

root = os.path.join(get_module_dir(quodlibet), "ext")
for entry in os.listdir(root):
    if entry.startswith("_"):
        continue
    path = os.path.join(root, entry)
    if not os.path.isdir(path):
        continue
    PLUGIN_DIRS.append(path)

PLUGIN_DIRS.append(os.path.join(util.get_module_dir(), "test_plugins"))

ms = ModuleScanner(PLUGIN_DIRS)

ms.rescan()

# make sure plugins only raise expected errors
for name, err in ms.failures.items():
    exc = err.exception
    msg = (f"{name!r} plugin shouldn't have raised {type(exc).__name__} but did "
           f"({exc!r}).")
    assert isinstance(exc, PluginImportError | ImportError), msg


plugins = {}
modules = {}
for module in ms.modules.values():
    for plugin in list_plugins(module.module):
        plugins[plugin.PLUGIN_ID] = Plugin(plugin)
        modules[plugin.PLUGIN_ID] = module.module


class PluginTestCase(TestCase):
    """Base class for all plugin tests"""

    plugins = plugins
    modules = modules
