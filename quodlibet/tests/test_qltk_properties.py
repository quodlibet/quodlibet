from tests import TestCase, add

import gtk

from formats._audio import AudioFile
from qltk.properties import SongProperties
from qltk.watcher import SongWatcher

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
        self.watcher = SongWatcher()

    def test_onesong(self):
        self.window = SongProperties(self.watcher, [self.af1])

    def test_twosong(self):
        self.window = SongProperties(self.watcher, [self.af2, self.af1])

    def test_changed(self):
        self.test_twosong()
        self.window.hide()
        self.watcher.emit('changed', [self.af2])
        while gtk.events_pending(): gtk.main_iteration()

    def test_removed(self):
        self.test_twosong()
        self.window.hide()
        self.watcher.emit('removed', [self.af2])
        while gtk.events_pending(): gtk.main_iteration()

    def tearDown(self):
        try: self.window.destroy()
        except AttributeError: pass
        else: del(self.window)
        self.watcher.destroy()
        del(SongProperties.plugins)
add(TSongProperties)
