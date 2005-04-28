from unittest import TestCase
from tests import registerCase
import os, sys
sys.modules['dircache'] = os # cheat the dircache effects
from tempfile import mkstemp, mkdtemp
from plugins import PluginManager

class TestPlugins(TestCase):

    def setUp(self):
        self.tempdir = mkdtemp()
        self.pm = PluginManager(folders=[self.tempdir])
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
            file.write("class Foo:\n")
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

    def test_name_only_has_no_plugins(self):
        dirname = self.create_plugin(name='NameOnly')
        self.pm.rescan()
        self.assertEquals(self.pm.list(), [])

    def test_desc_only_has_no_plugins(self):
        dirname = self.create_plugin(desc='DescOnly')
        self.pm.rescan()
        self.assertEquals(self.pm.list(), [])

    def test_name_and_desc_still_none(self):
        dirname = self.create_plugin(name='Name', desc='Desc')
        self.pm.rescan()
        self.assertEquals(self.pm.list(), [])

    def test_name_and_desc_plus_func_is_one(self):
        self.create_plugin(name='Name', desc='Desc', funcs=['plugin_song'])
        self.pm.rescan()
        self.assertEquals(len(self.pm.list()), 1)

    def test_additional_functions_still_only_one(self):
        self.create_plugin(name='Name', desc='Desc',
                funcs=['plugin_song', 'plugin_on_changed'])
        self.pm.rescan()
        self.assertEquals(len(self.pm.list()), 1)

    def test_two_plugins_are_two(self):
        self.create_plugin(name='Name', desc='Desc', funcs=['plugin_song'])
        self.create_plugin(name='Name2', desc='Desc2',
                funcs=['plugin_on_changed'])
        self.pm.rescan()
        self.assertEquals(len(self.pm.list()), 2)

class TestSongWrapper(TestCase):
    from plugins import SongWrapper
    from formats.audio import AudioFile

    def test_setitem(self):
        w = self.SongWrapper(self.AudioFile(
            {"title": "woo", "~filename": "/dev/null"}))
        self.failIf(w._was_updated())
        self.failUnlessEqual(w["title"], "woo")
        w["title"] = "bar"
        self.failUnless(w._was_updated())
        self.failUnlessEqual(w["title"], "bar")

    def test_not_really_updated(self):
        w = self.SongWrapper(self.AudioFile(
            {"title": "woo", "~filename": "/dev/null"}))
        self.failIf(w._was_updated())
        w["title"] = "woo"
        self.failIf(w._was_updated())
        w["title"] = "quux"
        self.failUnless(w._was_updated())

registerCase(TestPlugins)
registerCase(TestSongWrapper)
