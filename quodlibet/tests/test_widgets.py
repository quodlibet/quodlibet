from unittest import TestCase
from tests import registerCase, Mock
import os, gtk
import widgets
from widgets import DirectoryTree, EmptyBar, SearchBar, PlayList

import config

class TestDirTree(TestCase):
    def test_initial(self):
        for path in ["/", "/home", os.environ["HOME"], "/usr/bin"]:
            dirlist = DirectoryTree(path)
            model, rows = dirlist.get_selection().get_selected_rows()
            selected = [model[row][0] for row in rows]
            dirlist.destroy()
            self.failUnlessEqual([path], selected)

    def test_bad_initial(self):
        for path in ["/", os.environ["HOME"]]:
            newpath = os.path.join(path, "bin/file/does/not/exist")
            dirlist = DirectoryTree(newpath)
            model, rows = dirlist.get_selection().get_selected_rows()
            selected = [model[row][0] for row in rows]
            dirlist.destroy()
            self.failUnlessEqual([path], selected)

class TestEmptyBar(TestCase):
    def setUp(self):
        self._bar = EmptyBar(self._check_cb)

    def _check_cb(self, query, sort):
        self.failUnlessEqual(query, self._expected)
        del(self._expected)

    def test_initial(self):
        self._bar.set_text("a test")
        self._expected = "a test"
        self._bar.activate()

    def test_restore(self):
        self._bar.set_text("a test")
        self._bar.save()
        self._bar.set_text("not a test")
        self._bar.restore()
        self._expected = "a test"
        self._bar.activate()

    def test_can_filter(self):
        for key in ["artist", "album", "dummy", "~#track", "woo~bar~fake"]:
            self.failUnless(self._bar.can_filter(key))

    # not the best tests, but until we get a more structured way of
    # comparing queries they'll do...
    def test_filter_num(self):
        self._expected = "|(#(track = 3), #(track = 4))"
        self._bar.filter("~#track", [3, 4])

    def test_filter_text(self):
        self._expected = "artist = 'some guy'c"
        self._bar.filter("artist", ["some guy"])

    def tearDown(self):
        self._bar.destroy()

# SearchBar shares most of its code with EmptyBar, except for its
# implementation of activate(). So all we need to test is set_text and
# save/restore.
class TestSearchBar(TestCase):
    def setUp(self):
        self._bar = SearchBar(self._check_cb)
    
    def _check_cb(self, query, sort):
        self.failUnlessEqual(query, self._expected)
        del(self._expected)

    def test_initial(self):
        self._bar.set_text("a test")
        self._expected = "a test"
        self._bar.activate()

    def test_savenosave(self):
        bar = SearchBar(self._check_cb, save=False)
        bar.set_text("a test")
        bar.save()
        bar.set_text("another test")
        self._expected = "another test"
        bar.activate()
        bar.restore()
        self._expected = "a test"
        bar.activate()
        bar.destroy()

    def test_restore(self):
        self._bar.set_text("a test")
        self._bar.save()
        self._bar.set_text("not a test")
        self._bar.restore()
        self._expected = "a test"
        self._bar.activate()

    def tearDown(self):
        self._bar.destroy()

class TestPlayList(TestCase):
    def test_normalize_safe(self):
        for string in ["", "foo", "bar", "a_title", "some_keys"]:
            self.failUnlessEqual(string, PlayList.normalize_name(string))

    def test_normalize_unsafe(self):
        for string in ["%%%", "bad_ string", "<woo>", "|%more%20&tests",
                       "% % % %", "   ", ":=)", "#!=", "mixed # strings",
                       "".join(PlayList.BAD)]:
            nstring = PlayList.normalize_name(string)
            self.failIfEqual(string, nstring)
            self.failUnlessEqual(string, PlayList.prettify_name(nstring))

class StopAfterTest(TestCase):
    def test_active(self):
        w = widgets.MainWindow.StopAfterMenu()
        self.failIf(w.active)
        for b in [True, False, True, False, False]:
            w.active = b
            if b: self.failUnless(w.active)
            else: self.failIf(w.active)
        w.destroy()

registerCase(TestDirTree)
registerCase(TestEmptyBar)
registerCase(TestSearchBar)
registerCase(TestPlayList)
registerCase(StopAfterTest)

