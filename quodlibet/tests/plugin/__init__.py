from tests import TestCase
from quodlibet.util.modulescanner import ModuleScanner
from quodlibet.plugins import list_plugins
import sys
import os

# Nasty hack to allow importing of plugins...
PLUGIN_DIR = os.path.abspath(os.path.join(sys.path[0], '../plugins'))
TEST_PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "test_plugins")

ms = ModuleScanner([PLUGIN_DIR, TEST_PLUGIN_DIR])
ms.rescan()
plugins = {}
modules = {}
for name, module in ms.modules.iteritems():
    for plugin in list_plugins(module):
        plugins[plugin.PLUGIN_ID] = plugin
        modules[plugin.PLUGIN_ID] = module

class PluginTestCase(TestCase):
    """Base class for all plugin tests"""
    plugins = plugins
    modules = modules
