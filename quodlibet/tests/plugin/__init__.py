from tests import TestCase
from quodlibet.util.modulescanner import ModuleScanner
from quodlibet.plugins import list_plugins
import sys
import os

# Nasty hack to allow importing of plugins...
PLUGIN_DIR = os.path.abspath(os.path.join(sys.path[0], '../plugins'))

ms = ModuleScanner([PLUGIN_DIR])
ms.rescan()
plugins = {}
for name, module in ms.modules.iteritems():
    for plugin in list_plugins(module):
        plugins[plugin.PLUGIN_ID] = plugin

class PluginTestCase(TestCase):
    """Base class for all plugin tests"""
    plugins = plugins
