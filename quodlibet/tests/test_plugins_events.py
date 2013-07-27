from tests import TestCase, add, mkstemp, mkdtemp

import os
import sys

from quodlibet import player
from quodlibet.library import SongLibrarian
from quodlibet.plugins import PluginManager
from quodlibet.plugins.events import EventPluginHandler


class TEventPlugins(TestCase):

    def setUp(self):
        self.tempdir = mkdtemp()
        self.pm = PluginManager(folders=[self.tempdir])
        self.lib = SongLibrarian()
        self.player = player.init("nullbe").init(self.lib)
        self.handler = EventPluginHandler(
            librarian=self.lib, player=self.player)
        self.pm.register_handler(self.handler)
        self.pm.rescan()
        self.assertEquals(self.pm.plugins, [])

    def tearDown(self):
        self.pm.quit()
        for f in os.listdir(self.tempdir):
            os.remove(os.path.join(self.tempdir, f))
        os.rmdir(self.tempdir)

    def create_plugin(self, name='', funcs=None):
        fd, fn = mkstemp(suffix='.py', text=True, dir=self.tempdir)
        file = os.fdopen(fd, 'w')

        file.write("from quodlibet.plugins.events import EventPlugin\n")
        file.write("log = []\n")
        file.write("class %s(EventPlugin):\n" % name)
        indent = '    '
        file.write("%spass\n" % indent)

        if name:
            file.write("%sPLUGIN_ID = %r\n" % (indent, name))
            file.write("%sPLUGIN_NAME = %r\n" % (indent, name))

        for f in (funcs or []):
            file.write("%sdef %s(s, *args): log.append((%r, args))\n" %
                       (indent, f, f))
        file.flush()
        file.close()

    def _get_calls(self, plugin):
        mod = sys.modules[type(plugin).__module__]
        return mod.log

    def test_found(self):
        self.create_plugin(name='Name')
        self.pm.rescan()
        self.assertEquals(len(self.pm.plugins), 1)

    def test_player_paused(self):
        self.create_plugin(name='Name', funcs=["plugin_on_paused"])
        self.pm.rescan()
        self.assertEquals(len(self.pm.plugins), 1)
        plugin = self.pm.plugins[0]
        self.pm.enable(plugin, True)
        self.player.emit("paused")
        self.failUnlessEqual([("plugin_on_paused", tuple())],
                             self._get_calls(plugin))

    def test_lib_changed(self):
        self.create_plugin(name='Name', funcs=["plugin_on_changed"])
        self.pm.rescan()
        self.assertEquals(len(self.pm.plugins), 1)
        plugin = self.pm.plugins[0]
        self.pm.enable(plugin, True)
        self.lib.emit("changed", [None])
        self.failUnlessEqual([("plugin_on_changed", ([None],))],
                             self._get_calls(plugin))

add(TEventPlugins)
