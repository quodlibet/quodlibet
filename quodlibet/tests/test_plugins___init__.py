from unittest import TestCase
from tests import registerCase
import os, sys
from tempfile import mkstemp, mkdtemp
from plugins import PluginManager

class TPluginManager(TestCase):

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

class TSongWrapper(TestCase):
    from plugins import SongWrapper
    from formats._audio import AudioFile

    psong = AudioFile({
        "~filename": "does not/exist",
        "title": "more songs",
        "discnumber": "2/2", "tracknumber": "1",
        "artist": "Foo\nI have two artists", "album": "Bar" })
    pwrap = SongWrapper(psong)

    def setUp(self):
        self.wrap = self.SongWrapper(self.AudioFile(
            {"title": "woo", "~filename": "/dev/null"}))

    def test_slots(self):
        def breakme(): self.wrap.woo = 1
        self.failUnlessRaises(AttributeError, breakme)

    def test_cmp(self):
        songs = [self.SongWrapper(self.AudioFile({"tracknumber": str(i)}))
                 for i in range(10)]
        songs.reverse()
        songs.sort()
        self.failUnlessEqual([s("~#track") for s in songs], range(10))

    def test_needs_write_yes(self):
        self.failIf(self.wrap._needs_write)
        self.wrap["woo"] = "bar"
        self.failUnless(self.wrap._needs_write)

    def test_needs_write_no(self):
        self.failIf(self.wrap._needs_write)
        self.wrap["~woo"] = "bar"
        self.failIf(self.wrap._needs_write)

    def test_getitem(self):
        self.failUnlessEqual(self.wrap["title"], "woo")

    def test_get(self):
        self.failUnlessEqual(self.wrap.get("title"), "woo")
        self.failUnlessEqual(self.wrap.get("dne"), None)
        self.failUnlessEqual(self.wrap.get("dne", "huh"), "huh")

    def test_delitem(self):
        self.failUnless("title" in self.wrap)
        del(self.wrap["title"])
        self.failIf("title" in self.wrap)
        self.failUnless(self.wrap._needs_write)

    def test_realkeys(self):
        self.failUnlessEqual( self.pwrap.realkeys(), self.psong.realkeys())

    def test_website(self):
        self.failUnlessEqual(self.pwrap.website(), self.psong.website())

    def test_find_cover(self):
        self.failUnlessEqual(self.pwrap.find_cover(), self.psong.find_cover())

    def test_can_change(self):
        for key in ["~foo", "title", "whee", "a test", "foo=bar", ""]:
            self.failUnlessEqual(
                self.pwrap.can_change(key), self.psong.can_change(key))

    def test_comma(self):
        for key in ["title", "artist", "album", "notexist", "~#length"]:
            self.failUnlessEqual(self.pwrap.comma(key), self.psong.comma(key))

    def test_list(self):
        for key in ["title", "artist", "album", "notexist", "~#length"]:
            self.failUnlessEqual(self.pwrap.list(key), self.psong.list(key))

    def test_dicty(self):
        self.failUnlessEqual(self.pwrap.keys(), self.psong.keys())
        self.failUnlessEqual(self.pwrap.values(), self.psong.values())
        self.failUnlessEqual(self.pwrap.items(), self.psong.items())

    def test_mtime(self):
        self.wrap._song.sanitize()
        self.failUnless(self.wrap.valid())
        self.wrap["~#mtime"] = os.path.getmtime("/dev/null") - 2
        self.wrap._updated = False
        self.failIf(self.wrap.valid())

    def test_setitem(self):
        self.failIf(self.wrap._was_updated())
        self.wrap["title"] = "bar"
        self.failUnless(self.wrap._was_updated())
        self.failUnlessEqual(self.wrap["title"], "bar")

    def test_not_really_updated(self):
        self.failIf(self.wrap._was_updated())
        self.wrap["title"] = "woo"
        self.failIf(self.wrap._was_updated())
        self.wrap["title"] = "quux"
        self.failUnless(self.wrap._was_updated())

    def test_new_tag(self):
        self.failIf(self.wrap._was_updated())
        self.wrap["version"] = "bar"
        self.failUnless(self.wrap._was_updated())

registerCase(TPluginManager)
registerCase(TSongWrapper)
