from tests import TestCase, add

import os

from tempfile import mkstemp, mkdtemp

from quodlibet.formats._audio import AudioFile
from quodlibet.plugins import PluginManager
from quodlibet.qltk.songsmenu import SongsMenuPluginHandler

class TSongsMenuPlugins(TestCase):

    def setUp(self):
        self.tempdir = mkdtemp()
        self.pm = PluginManager(folders=[self.tempdir])
        self.handler = SongsMenuPluginHandler()
        self.pm.register_handler(self.handler)
        self.pm.rescan()
        self.assertEquals(self.pm.plugins, [])

    def tearDown(self):
        self.pm.quit()
        for f in os.listdir(self.tempdir):
            os.remove(os.path.join(self.tempdir,f))
        os.rmdir(self.tempdir)

    def create_plugin(self, id= '', name='', desc='', icon='', funcs=None, mod=False):
        fd, fn = mkstemp(suffix='.py', text=True, dir=self.tempdir)
        file = os.fdopen(fd, 'w')

        if mod:
            indent = ''
        else:
            file.write("from quodlibet.plugins.songsmenu import SongsMenuPlugin\n")
            file.write("class %s(SongsMenuPlugin):\n" % name)
            indent = '    '
            file.write("%spass\n" % indent)

        if name: file.write("%sPLUGIN_ID = %r\n" % (indent, name))
        if name: file.write("%sPLUGIN_NAME = %r\n" % (indent, name))
        if desc: file.write("%sPLUGIN_DESC = %r\n" % (indent, desc))
        if icon: file.write("%sPLUGIN_ICON = %r\n" % (indent, icon))
        for f in (funcs or []):
            if f in ["__init__"]:
                file.write("%sdef %s(*args): pass\n" % (indent, f))
            else:
                file.write("%sdef %s(*args): return args\n" % (indent, f))
        file.flush()
        file.close()

    def test_empty_has_no_plugins(self):
        self.pm.rescan()
        self.assertEquals(self.pm.plugins, [])

    def test_name_and_desc_plus_func_is_one(self):
        self.create_plugin(name='Name', desc='Desc', funcs=['plugin_song'])
        self.pm.rescan()
        self.assertEquals(len(self.pm.plugins), 1)

    def test_additional_functions_still_only_one(self):
        self.create_plugin(name='Name', desc='Desc',
                funcs=['plugin_song', 'plugin_songs'])
        self.pm.rescan()
        self.assertEquals(len(self.pm.plugins), 1)

    def test_two_plugins_are_two(self):
        self.create_plugin(name='Name', desc='Desc', funcs=['plugin_song'])
        self.create_plugin(name='Name2', desc='Desc2',
                funcs=['plugin_albums'])
        self.pm.rescan()
        self.assertEquals(len(self.pm.plugins), 2)

    def test_disables_plugin(self):
        self.create_plugin(name='Name', desc='Desc', funcs=['plugin_song'])
        self.pm.rescan()
        self.failIf(self.pm.enabled(self.pm.plugins[0]))

    def test_enabledisable_plugin(self):
        self.create_plugin(name='Name', desc='Desc', funcs=['plugin_song'])
        self.pm.rescan()
        plug = self.pm.plugins[0]
        self.pm.enable(plug, True)
        self.failUnless(self.pm.enabled(plug))
        self.pm.enable(plug, False)
        self.failIf(self.pm.enabled(plug))

    def test_ignores_broken_plugin(self):
        self.create_plugin(name="Broken", desc="Desc",
                           funcs=["__init__", "plugin_song"])
        self.pm.rescan()
        plug = self.pm.plugins[0]
        self.pm.enable(plug, True)
        menu = self.handler.Menu(None, None, [AudioFile()])
        self.failIf(menu and menu.get_children())

    def test_Menu(self):
        self.create_plugin(name='Name', desc='Desc', funcs=['plugin_song'])
        self.handler.Menu(None, None, [AudioFile()])

add(TSongsMenuPlugins)
