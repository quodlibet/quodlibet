from tests import AbstractTestCase, skipUnless
from quodlibet.util.modulescanner import ModuleScanner
from quodlibet.plugins import list_plugins, Plugin, PluginImportException
import quodlibet
import sys
import os


# Nasty hack to allow importing of plugins...
PLUGIN_DIRS = []

root = os.path.join(quodlibet.__path__[0], "ext")
for entry in os.listdir(root):
    if entry.startswith("_"):
        continue
    path = os.path.join(root, entry)
    if not os.path.isdir(path):
        continue
    PLUGIN_DIRS.append(path)

PLUGIN_DIRS.append(os.path.join(os.path.dirname(__file__), "test_plugins"))

ms = ModuleScanner(PLUGIN_DIRS)
ms.rescan()

# make sure plugins only raise expected errors
for name, err in ms.failures.items():
    assert issubclass(type(err.exception), PluginImportException)

plugins = {}
modules = {}
for name, module in ms.modules.iteritems():
    for plugin in list_plugins(module.module):
        plugins[plugin.PLUGIN_ID] = Plugin(plugin)
        modules[plugin.PLUGIN_ID] = module.module


def init_fake_app():
    from quodlibet import app

    from quodlibet import browsers
    from quodlibet.player.nullbe import NullPlayer
    from quodlibet.library.libraries import SongFileLibrary
    from quodlibet.library.librarians import SongLibrarian
    from quodlibet.qltk.quodlibetwindow import QuodLibetWindow

    browsers.init()
    app.player = NullPlayer()
    app.library = SongFileLibrary()
    app.library.librarian = SongLibrarian()
    app.window = QuodLibetWindow(app.library, app.player, headless=True)


def destroy_fake_app():
    from quodlibet import app

    app.window.destroy()
    app.library.destroy()
    app.library.librarian.destroy()
    app.player.destroy()

    app.window = app.library = app.player = None


class PluginTestCase(AbstractTestCase):
    """Base class for all plugin tests"""
    plugins = plugins
    modules = modules
