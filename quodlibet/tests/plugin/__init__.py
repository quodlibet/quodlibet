from tests import TestCase
from quodlibet.util.modulescanner import load_module
import sys
import os

# Nasty hack to allow importing of plugins...
PLUGIN_DIR = os.path.abspath(os.path.join(sys.path[0], '../plugins'))


def import_plugin(subdir, fn):
    dir = os.path.join(PLUGIN_DIR, subdir)
    module = load_module(fn, "quodlibet.fake.test.plugin", dir)
    print_d("Loaded module from (%s) = %s" % (dir, module))
    return module


class PluginTestCase(TestCase):
    """Base class for all plugin tests"""
