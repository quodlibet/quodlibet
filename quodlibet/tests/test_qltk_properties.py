from tests import TestCase, add

import gtk

from quodlibet.formats._audio import AudioFile
from quodlibet.qltk.properties import SongProperties
from quodlibet.library import SongLibrary
from quodlibet import config

class DummyPlugins(object):
    def rescan(self): pass
    def find_subclasses(self, *args): return []
    def TagsFromPathPlugins(self): return []
    def RenamePlugins(self): return []
    def EditTagsPlugins(self): return []

class TSongProperties(TestCase):
    af1 = AudioFile({"title": "woo"})
    af1.sanitize("invalid")
    af2 = AudioFile({"title": "bar", "album": "quux"})
    af2.sanitize("alsoinvalid")

    def setUp(self):
        SongProperties.plugins = DummyPlugins()
        config.init()
        self.library = SongLibrary()

    def test_onesong(self):
        self.window = SongProperties(self.library, [self.af1])

    def test_twosong(self):
        self.window = SongProperties(self.library, [self.af2, self.af1])

    def test_changed(self):
        self.test_twosong()
        self.window.hide()
        self.library.emit('changed', [self.af2])
        while gtk.events_pending(): gtk.main_iteration()

    def test_removed(self):
        self.test_twosong()
        self.window.hide()
        self.library.emit('removed', [self.af2])
        while gtk.events_pending(): gtk.main_iteration()

    def tearDown(self):
        try: self.window.destroy()
        except AttributeError: pass
        else: del(self.window)
        self.library.destroy()
        del(SongProperties.plugins)
        config.quit()
add(TSongProperties)
