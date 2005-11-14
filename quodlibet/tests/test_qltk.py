from unittest import TestCase
from tests import registerCase, Mock
import os, gtk, qltk
from StringIO import StringIO

class TSongWatcher(TestCase):
    def setUp(self):
        self.watcher = qltk.SongWatcher()

    def __changed(self, watcher, song, expected):
        self.failUnlessEqual(expected.pop(0), song)

    def __test_signal(self, sig):
        expected = [[0], [1], [2], [3], [4], [5]]
        self.watcher.connect(sig, self.__changed, expected)
        map(getattr(self.watcher, sig), list(expected))
        while gtk.events_pending(): gtk.main_iteration()
        self.failIf(expected)

    def test_changed(self): self.__test_signal('changed')
    def test_removed(self): self.__test_signal('removed')
    def test_missing(self): self.__test_signal('missing')

    def __test_started_cb(self, watcher, song):
        self.failUnlessEqual(watcher.time[0], 0)
        self.failUnlessEqual(watcher.song, song)
        if song: self.failUnlessEqual(watcher.time[1], song["~#length"]*1000)
        else: self.failUnlessEqual(watcher.time[1], 1)
        self.__count += 1

    def test_started(self):
        self.__count = 0
        self.watcher.connect('song-started', self.__test_started_cb)
        self.watcher.song_started(None)
        while gtk.events_pending(): gtk.main_iteration()
        self.watcher.song_started({"~#length": 10})
        while gtk.events_pending(): gtk.main_iteration()
        self.watcher.song_started(None)
        while gtk.events_pending(): gtk.main_iteration()
        self.watcher.song_started({"~#length": 12})
        while gtk.events_pending(): gtk.main_iteration()
        self.failUnlessEqual(4, self.__count)

    def __refresh_cb(self, watcher): self.__refreshed = True
    def test_refresh(self):
        self.__refreshed = False
        self.watcher.connect('refresh', self.__refresh_cb)
        self.watcher.refresh()
        while gtk.events_pending(): gtk.main_iteration()
        self.failUnless(self.__refreshed)

    def __ended_cb(self, watcher, song, stopped):
        if song & 1: self.failIf(stopped)
        else: self.failUnless(stopped)
        watcher.song = song

    def test_ended(self):
        self.watcher.connect('song-ended', self.__ended_cb)
        self.watcher.song_ended(1, False)
        self.watcher.song_ended(2, True)
        self.watcher.song_ended(3, False)
        self.watcher.song_ended(4, True)
        while gtk.events_pending(): gtk.main_iteration()
        self.failUnlessEqual(4, self.watcher.song)

    def __paused_cb(self, watcher): self.__paused += 1
    def __unpaused_cb(self, watcher): self.__unpaused += 1
    def test_paused(self):
        self.__paused = 0
        self.__unpaused = 0
        self.watcher.connect('paused', self.__paused_cb)
        self.watcher.connect('unpaused', self.__unpaused_cb)
        for i in range(4): self.watcher.set_paused(True)
        for i in range(6): self.watcher.set_paused(False)
        while gtk.events_pending(): gtk.main_iteration()
        self.failUnlessEqual(4, self.__paused)
        self.failUnlessEqual(6, self.__unpaused)

    def tearDown(self):
        self.watcher.destroy()

registerCase(TSongWatcher)

class TestNotebook(TestCase):
    def test_widget_str(self):
        n = qltk.Notebook()
        c = gtk.VBox()
        n.append_page(c, "A Test")
        self.failUnlessEqual("A Test", n.get_tab_label(c).get_text())
        n.destroy()

    def test_widget_label(self):
        l = gtk.Label("A Test")
        n = qltk.Notebook()
        c = gtk.VBox()
        n.append_page(c, l)
        self.failUnless(l is n.get_tab_label(c))
        c.destroy()

    def test_widget_error(self):
        n = qltk.Notebook()
        w = gtk.VBox()
        self.failUnlessRaises(TypeError, n.append_page, w)
        w.destroy()
        n.destroy()

class TestComboSave(TestCase):
    def test_apprepend(self):
        c = qltk.ComboBoxEntrySave()
        self.failUnlessEqual([], c.get_text())
        c.append_text("line 1")
        c.append_text("line 2")
        c.prepend_text("line 0")
        self.failUnlessEqual(["line 0", "line 1", "line 2"], c.get_text())
        c.destroy()

    def test_initial(self):
        c = qltk.ComboBoxEntrySave(initial = ["line 1", "line 2"])
        self.failUnlessEqual(["line 1", "line 2"], c.get_text())
        c.destroy()

    def test_count(self):
        c = qltk.ComboBoxEntrySave(initial = ["line 1"], count = 2)
        self.failUnlessEqual(["line 1"], c.get_text())
        c.append_text("line 2")
        self.failUnlessEqual(["line 1", "line 2"], c.get_text())
        c.append_text("line 3")
        self.failUnlessEqual(["line 1", "line 2"], c.get_text())
        c.prepend_text("line 0")
        self.failUnlessEqual(["line 0", "line 1"], c.get_text())
        c.destroy()

    def test_read_filename(self):
        f = file("combo_test", "w")
        f.write("line 1\nline 2\nline 3\n")
        f.close()
        c = qltk.ComboBoxEntrySave("combo_test")
        self.failUnlessEqual(["line 1", "line 2", "line 3"], c.get_text())
        os.unlink("combo_test")
        c.destroy()

    def test_read_filelike(self):
        f = StringIO("line 1\nline 2\nline 3\n")
        c = qltk.ComboBoxEntrySave(f)
        self.failUnlessEqual(["line 1", "line 2", "line 3"], c.get_text())
        c.destroy()

    def test_write_filelike(self):
        f = StringIO()
        c = qltk.ComboBoxEntrySave(initial = ["line 1", "line 2", "line 3"])
        c.write(f)
        f.seek(0)
        c2 = qltk.ComboBoxEntrySave(f)
        self.failUnlessEqual(c.get_text(), c2.get_text())
        c.destroy()
        c2.destroy()

    def test_write_filename(self):
        c = qltk.ComboBoxEntrySave(initial = ["line 1", "line 2", "line 3"])
        c.write("combo_test")
        c2 = qltk.ComboBoxEntrySave("combo_test")
        self.failUnlessEqual(c.get_text(), c2.get_text())
        os.unlink("combo_test")
        c.destroy()
        c2.destroy()

    def test_write_filedir(self):
        self.failIf(os.path.isdir('notdir'))
        c = qltk.ComboBoxEntrySave(initial = ["line 1", "line 2", "line 3"])
        c.write("notdir/combo_test")
        c2 = qltk.ComboBoxEntrySave("notdir/combo_test")
        self.failUnlessEqual(c.get_text(), c2.get_text())
        os.unlink("notdir/combo_test")
        os.rmdir("notdir")
        c.destroy()
        c2.destroy()

    def test_initial_file_append(self):
        c = qltk.ComboBoxEntrySave(
            StringIO("line 0"), initial = ["line 1"])
        c.append_text("line 2")
        self.failUnlessEqual(["line 0", "line 1", "line 2"], c.get_text())
        c.destroy()

class TestWLW(TestCase):
    class DummyConnector(gtk.Window):
        count = 0
        def connect(self, *args): self.count += 1
        def disconnect(self, *args): self.count -= 1
        class Eater:
            def set_cursor(*args): pass
        window = Eater()
    
    def setUp(self):
        self.parent = self.DummyConnector()
        self.wlw = qltk.WaitLoadWindow(self.parent, 5, "a test", show=False)
        self.wlw.hide()

    def test_none(self):
        wlw = qltk.WaitLoadWindow(None, 5, "a test", show=False)
        wlw.step()
        wlw.destroy()

    def test_connect(self):
        self.failUnlessEqual(1, self.parent.count)

    def test_start(self):
        self.failUnlessEqual(0, self.wlw.current)
        self.failUnlessEqual(5, self.wlw.count)

    def test_step(self):
        self.failIf(self.wlw.step())
        self.failUnlessEqual(1, self.wlw.current)
        self.failIf(self.wlw.step())
        self.failIf(self.wlw.step())
        self.failUnlessEqual(3, self.wlw.current)

    def test_destroy(self):
        self.wlw.destroy()
        self.failUnlessEqual(0, self.parent.count)

    def tearDown(self):
        self.wlw.destroy()

class TGetTopParent(TestCase):
    def test_gtp(self):
        w = gtk.HBox(); l = gtk.Label()
        self.failUnlessEqual(qltk.get_top_parent(w), w)
        self.failUnlessEqual(qltk.get_top_parent(l), l)
        w.destroy(); l.destroy()

    def test_gtp_packed(self):
        w = gtk.HBox(); l = gtk.Label(); w.pack_start(l)
        self.failUnlessEqual(qltk.get_top_parent(w), w)
        self.failUnlessEqual(qltk.get_top_parent(l), w)
        w.destroy(); l.destroy()
registerCase(TGetTopParent)

registerCase(TestNotebook)
registerCase(TestComboSave)
registerCase(TestWLW)

