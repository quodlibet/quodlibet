from tests import AbstractTestCase, skipUnless
from quodlibet.util.modulescanner import ModuleScanner
from quodlibet.plugins import list_plugins, Plugin
import quodlibet
import sys
import os


# Nasty hack to allow importing of plugins...
PLUGIN_DIRS = []

root = os.path.join(quodlibet.__path__[0], "ext")
for entry in os.listdir(root):
    path = os.path.join(root, entry)
    if not os.path.isdir(path):
        continue
    PLUGIN_DIRS.append(path)

PLUGIN_DIRS.append(os.path.join(os.path.dirname(__file__), "test_plugins"))

ms = ModuleScanner(PLUGIN_DIRS)
ms.rescan()
plugins = {}
modules = {}
for name, module in ms.modules.iteritems():
    for plugin in list_plugins(module.module):
        plugins[plugin.PLUGIN_ID] = Plugin(plugin)
        modules[plugin.PLUGIN_ID] = module.module


class PluginTestCase(AbstractTestCase):
    """Base class for all plugin tests"""
    plugins = plugins
    modules = modules
