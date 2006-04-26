import os

from unittest import TestCase
from tests import registerCase

from tempfile import mkstemp, mkdtemp
from plugins.songsmenu import SongsMenuPlugins
from formats._audio import AudioFile

class TSongsMenuPlugins(TestCase):

    def setUp(self):
        self.tempdir = mkdtemp()
        self.pm = SongsMenuPlugins(folders=[self.tempdir])
        self.pm.rescan()
        self.assertEquals(self.pm.list(), [])

    def tearDown(self):
        for f in os.listdir(self.tempdir):
            os.remove(os.path.join(self.tempdir,f))
        os.rmdir(self.tempdir)

    def create_plugin(self, name='', desc='', icon='', funcs=None, mod=False):
        fd, fn = mkstemp(suffix='.py', text=True, dir=self.tempdir)
        file = os.fdopen(fd, 'w')

        if mod:
            indent = ''
        else:
            file.write("from plugins.songsmenu import SongsMenuPlugin\n")
            file.write("class %s(SongsMenuPlugin):\n" % name)
            indent = '    '
            file.write("%spass\n" % indent)

        if name: file.write("%sPLUGIN_NAME = %r\n" % (indent, name))
        if desc: file.write("%sPLUGIN_DESC = %r\n" % (indent, desc))
        if icon: file.write("%sPLUGIN_ICON = %r\n" % (indent, icon))
        for f in (funcs or []):
            file.write("%sdef %s(*args): return args\n" % (indent, f))
        file.flush()
        file.close()

    def test_empty_has_no_plugins(self):
        dirname = self.create_plugin()
        self.pm.rescan()
        self.assertEquals(self.pm.list(), [])

    def test_name_and_desc_plus_func_is_one(self):
        self.create_plugin(name='Name', desc='Desc', funcs=['plugin_song'])
        self.pm.rescan()
        self.assertEquals(len(self.pm.list()), 1)

    def test_additional_functions_still_only_one(self):
        self.create_plugin(name='Name', desc='Desc',
                funcs=['plugin_song', 'plugin_songs'])
        self.pm.rescan()
        self.assertEquals(len(self.pm.list()), 1)

    def test_two_plugins_are_two(self):
        self.create_plugin(name='Name', desc='Desc', funcs=['plugin_song'])
        self.create_plugin(name='Name2', desc='Desc2',
                funcs=['plugin_albums'])
        self.pm.rescan()
        self.assertEquals(len(self.pm.list()), 2)

    def test_disables_plugin(self):
        self.create_plugin(name='Name', desc='Desc', funcs=['plugin_song'])
        self.pm.rescan()
        self.failIf(self.pm.enabled(self.pm.list()[0]))

    def test_enabledisable_plugin(self):
        self.create_plugin(name='Name', desc='Desc', funcs=['plugin_song'])
        self.pm.rescan()
        plug = self.pm.list()[0]
        self.pm.enable(plug, True)
        self.failUnless(self.pm.enabled(plug))
        self.pm.enable(plug, False)
        self.failIf(self.pm.enabled(plug))

    def test_ignores_broken_plugin(self):
        self.create_plugin(name="Name", desc="Desc",
                           funcs=["__init__", "plugin_song"])
        self.pm.rescan()
        plug = self.pm.list()[0]
        self.pm.enable(plug, True)
        menu = self.pm.Menu(None, None, [AudioFile()])
        self.failIf(menu.get_children())

    def test_Menu(self):
        self.create_plugin(name='Name', desc='Desc', funcs=['plugin_song'])
        menu = self.pm.Menu(None, None, [AudioFile()])

registerCase(TSongsMenuPlugins)
