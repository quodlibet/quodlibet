# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
import os
import shutil

from gi.repository import Gtk

from quodlibet.formats import AudioFile
from quodlibet.library.base import (Library, iter_paths, PicklingMixin)
from quodlibet.util import connect_obj, is_windows
from senf import fsnative
from tests import TestCase, mkstemp, mkdtemp, skipIf


class Fake(int):
    def __init__(self, _):
        self.key = int(self)


def Frange(*args):
    return list(map(Fake, range(*args)))


class FakeSong(Fake):
    def list(self, tag):
        # Turn tag_values into a less-than query, for testing.
        if tag <= self:
            return []
        else:
            return [int(self)]

    def rename(self, newname):
        self.key = newname


class AlbumSong(AudioFile):
    """A mock AudioFile belong to one of three albums,
    based on a single number"""

    def __init__(self, num, album=None):
        super().__init__()
        self["~filename"] = fsnative(u"file_%d.mp3" % (num + 1))
        self["title"] = "Song %d" % (num + 1)
        self["artist"] = "Fakeman"
        if album is None:
            self["album"] = "Album %d" % (num % 3 + 1)
        else:
            self["album"] = album
        self["labelid"] = self["album"]


class FakeSongFile(FakeSong):
    _valid = True
    _exists = True
    _mounted = True

    @property
    def mountpoint(self):
        return "/" if self._mounted else "/FAKE"

    def valid(self):
        return self._valid

    def exists(self):
        return self._exists

    def reload(self):
        if self._exists:
            self._valid = True
        else:
            raise IOError("doesn't exist")

    def mounted(self):
        return self._mounted


# Custom range functions, to generate lists of song-like objects
def FSFrange(*args):
    return list(map(FakeSongFile, range(*args)))


def FSrange(*args):
    return list(map(FakeSong, range(*args)))


def ASrange(*args):
    return list(map(AlbumSong, range(*args)))


class TLibrary(TestCase):
    Fake = Fake
    Frange = staticmethod(Frange)
    Library = Library

    def setUp(self):
        self.library = self.Library()
        self.added = []
        self.changed = []
        self.removed = []

        connect_obj(self.library, 'added', list.extend, self.added)
        connect_obj(self.library, 'changed', list.extend, self.changed)
        connect_obj(self.library, 'removed', list.extend, self.removed)

    def test_add(self):
        self.library.add(self.Frange(12))
        self.failUnlessEqual(self.added, self.Frange(12))
        del self.added[:]
        self.library.add(self.Frange(12, 24))
        self.failUnlessEqual(self.added, self.Frange(12, 24))

    def test_remove(self):
        self.library.add(self.Frange(10))
        self.assertTrue(self.library.remove(self.Frange(3, 6)))
        self.failUnlessEqual(self.removed, self.Frange(3, 6))

        # Neither the objects nor their keys should be present.
        self.failIf(self.Fake(3) in self.library)
        self.failUnless(self.Fake(6) in self.library)
        self.failIf(3 in self.library)
        self.failUnless(6 in self.library)

    def test_remove_when_not_present(self):
        self.assertFalse(self.library.remove([self.Fake(12)]))

    def test_changed(self):
        self.library.add(self.Frange(10))
        self.library.changed(self.Frange(5))
        while Gtk.events_pending():
            Gtk.main_iteration()
        self.failUnlessEqual(self.changed, self.Frange(5))

    def test_changed_not_present(self):
        self.library.add(self.Frange(10))
        self.library.changed(self.Frange(2, 20, 3))
        while Gtk.events_pending():
            Gtk.main_iteration()
        self.failUnlessEqual(set(self.changed), {2, 5, 8})

    def test_changed_none_present(self):
        self.library.changed(self.Frange(5))
        while Gtk.events_pending():
            Gtk.main_iteration()

    def test___iter__(self):
        self.library.add(self.Frange(10))
        self.failUnlessEqual(sorted(list(self.library)), self.Frange(10))

    def test___iter___empty(self):
        self.failIf(list(self.library))

    def test___len__(self):
        self.failUnlessEqual(len(self.library), 0)
        self.library.add(self.Frange(10))
        self.failUnlessEqual(len(self.library), 10)
        self.library.remove(self.Frange(3))
        self.failUnlessEqual(len(self.library), 7)

    def test___getitem__(self):
        self.library.add(self.Frange(10))
        self.failUnlessEqual(self.library[5], Fake(5))
        new = self.Fake(12)
        new.key = 100
        self.library.add([new])
        self.failUnlessEqual(self.library[100], new)
        self.failIf(12 in self.library)

    def test___getitem___not_present(self):
        self.library.add(self.Frange(10))
        self.failUnlessRaises(KeyError, self.library.__getitem__, 12)

    def test___contains__(self):
        self.library.add(self.Frange(10))
        new = self.Fake(12)
        new.key = 100
        self.library.add([new])
        for value in [0, 1, 2, 6, 9, 100, new]:
            # 0, 1, 2, 6, 9: all added by self.Frange
            # 100: key for new
            # new: is itself present
            self.failUnless(value in self.library, "didn't find %s" % value)

        for value in [-1, 10, 12, 101]:
            # -1, 10, 101: boundary values
            # 12: equal but non-key-equal to new
            self.failIf(value in self.library, "found %d" % value)

    def test_get(self):
        self.failUnless(self.library.get(12) is None)
        self.failUnless(self.library.get(12, "foo") == "foo")
        new = self.Fake(12)
        new.key = 100
        self.library.add([new])
        self.failUnless(self.library.get(12) is None)
        self.failUnless(self.library.get(100) is new)

    def test_keys(self):
        items = []
        for i in range(20):
            items.append(self.Fake(i))
            items[-1].key = i + 100
        self.library.add(items)
        self.failUnlessEqual(
            sorted(self.library.keys()), list(range(100, 120)))

    def test_values(self):
        items = []
        for i in range(20):
            items.append(self.Fake(i))
            items[-1].key = i + 100
        self.library.add(items)
        self.failUnlessEqual(sorted(self.library.values()), list(self.Frange(20)))

    def test_items(self):
        items = []
        for i in range(20):
            items.append(self.Fake(i))
            items[-1].key = i + 100
        self.library.add(items)
        expected = list(zip(range(100, 120), range(20)))
        self.failUnlessEqual(sorted(self.library.items()), expected)

    def test_has_key(self):
        self.failIf(self.library.has_key(10))
        new = self.Fake(10)
        new.key = 20
        self.library.add([new])
        self.failIf(self.library.has_key(10))
        self.failUnless(self.library.has_key(20))

    def tearDown(self):
        self.library.destroy()


class FakeAudioFile(AudioFile):

    def __init__(self, key):
        self._written = []
        self["~filename"] = fsnative(str(key))

    def write(self):
        self._written.append(self("~filename"))


def FakeAudioFileRange(*args):
    return list(map(FakeAudioFile, range(*args)))


class TPicklingMixin(TestCase):
    class PicklingMockLibrary(PicklingMixin, Library):
        """A library-like class that implements enough to test PicklingMixin"""

        def __init__(self):
            super().__init__(name="Mock")
            self._contents = {}
            # set up just enough of the library interface to work
            self.values = self._contents.values
            self.items = self._contents.items

        def add(self, items):
            for item in items:
                self._contents[item.key] = item

    Library = PicklingMockLibrary
    Frange = staticmethod(FakeAudioFileRange)

    def setUp(self):
        self.library = self.Library()

    def test_load_noexist(self):
        fd, filename = mkstemp()
        os.close(fd)
        os.unlink(filename)
        library = self.Library()
        library.load(filename)
        assert len(library) == 0

    def test_load_invalid(self):
        fd, filename = mkstemp()
        os.write(fd, b"nope")
        os.close(fd)
        try:
            library = self.Library()
            library.load(filename)
            assert len(library) == 0
        finally:
            os.unlink(filename)

    def test_save_load(self):
        fd, filename = mkstemp()
        os.close(fd)
        try:
            self.library.add(self.Frange(30))
            self.library.save(filename)

            library = self.Library()
            library.load(filename)
            for (k, v), (k2, v2) in zip(
                sorted(self.library.items()), sorted(library.items())):
                assert k == k2
                assert v.key == v2.key
        finally:
            os.unlink(filename)


class Titer_paths(TestCase):

    def setUp(self):
        # on osx the temp folder returned is a symlink
        self.root = os.path.realpath(mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_empty(self):
        assert list(iter_paths(self.root)) == []

    def test_one_file(self):
        fd, name = mkstemp(dir=self.root)
        os.close(fd)
        assert list(iter_paths(self.root)) == [name]

    def test_one_file_exclude(self):
        fd, name = mkstemp(dir=self.root)
        os.close(fd)
        assert list(iter_paths(self.root, exclude=[self.root])) == []
        assert list(iter_paths(self.root,
                               exclude=[os.path.dirname(self.root)])) == []
        assert list(iter_paths(self.root, exclude=[name])) == []
        assert list(iter_paths(self.root, exclude=[name + "a"])) == [name]

    @skipIf(is_windows(), "no symlink")
    def test_with_dir_symlink(self):
        child = mkdtemp(dir=self.root)
        link = os.path.join(self.root, "foo")
        os.symlink(child, link)
        fd, name = mkstemp(dir=link)
        os.close(fd)

        assert name not in list(iter_paths(self.root))
        assert list(iter_paths(link)) == list(iter_paths(child))

        assert list(iter_paths(link, exclude=[link])) == []
        assert list(iter_paths(child, exclude=[child])) == []
        assert list(iter_paths(link, exclude=[child])) == []

    @skipIf(is_windows(), "no symlink")
    def test_with_file(self):
        fd, name = mkstemp(dir=self.root)
        os.close(fd)
        link = os.path.join(self.root, "foo")
        os.symlink(name, link)

        assert list(iter_paths(self.root)) == [name, name]
        assert list(iter_paths(self.root, exclude=[link])) == [name]
        assert list(iter_paths(self.root, exclude=[name])) == []

    def test_hidden_dir(self):
        child = mkdtemp(dir=self.root, prefix=".")
        fd, name = mkstemp(dir=child)
        os.close(fd)
        assert list(iter_paths(child)) == []
        assert list(iter_paths(child, skip_hidden=False)) == [name]
        assert list(iter_paths(self.root)) == []
        assert list(iter_paths(self.root, skip_hidden=False)) == [name]

    def test_hidden_file(self):
        fd, name = mkstemp(dir=self.root, prefix=".")
        os.close(fd)

        assert list(iter_paths(self.root)) == []
