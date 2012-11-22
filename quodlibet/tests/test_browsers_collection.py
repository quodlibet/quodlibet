# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk

from tests import TestCase, add

from quodlibet import config

from quodlibet.browsers.collection import *
from quodlibet.formats._audio import AudioFile
from quodlibet.library import SongLibrary

SONGS = [
    AudioFile({"album": "one", "artist": "piman", "~filename": "/dev/null"}),
    AudioFile({"album": "two", "artist": "mu\nboris", "~filename": "/dev/zero"}),
    AudioFile({"album": "three", "artist": "boris", "~filename": "/bin/ls"}),
    AudioFile({"album": "three", "artist": "boris", "~filename": "/bin/ls2"}),
    AudioFile({"album": "four", "~filename": "/bin/ls3"}),
    ]
SONGS.sort()


class TCollectionPreferences(TestCase):
    def setUp(self):
        config.init()

    def tearDown(self):
        config.quit()

    def test_headers(self):
        value = [("foobar", 0), ("~people", 1)]
        save_headers(value)
        self.failUnlessEqual(get_headers(), value)

    def test_pref_dialog(self):
        d = PatternEditor()
        d.destroy()

add(TCollectionPreferences)


class TCollectionAlbums(TestCase):
    def setUp(self):
        l = SongLibrary()
        l.add(SONGS)
        l.albums.load()
        self.albums = l.albums

    def tearDown(self):
        del self.albums

    def test_build_tree(self):
        tags = [("~people", 0)]
        tree = build_tree(tags, self.albums)
        self.failUnless("mu" in tree)
        self.failUnless("boris" in tree)
        self.failUnless("piman" in tree)
        self.failUnless(UnknownNode in tree)
        self.failUnlessEqual(len(tree), 4)

    def test_build_tree_merge(self):
        tags = [("~people", 1)]
        tree = build_tree(tags, self.albums)
        self.failUnless(MultiNode in tree)
        self.failUnless(UnknownNode in tree)
        self.failUnless("boris" in tree)
        self.failUnless("piman" in tree)
        self.failUnlessEqual(len(tree), 4)

    def test_model(self):
        model = CollectionTreeStore()
        model.set_albums([("~people", 0)], self.albums)
        self.failUnlessEqual(len(model), 4)
        model.change_albums(self.albums)
        self.failUnlessEqual(len(model), 4)
        model.remove_albums(self.albums)
        self.failUnlessEqual(len(model), 0)

    def test_utils(self):
        model = CollectionTreeStore()
        model.set_albums([("~people", 0)], self.albums)
        a = self.albums.values()
        a.sort(key=lambda x: x.key)

        path = StoreUtils.get_path_for_album(model, a[0])
        albums = StoreUtils.get_albums_for_path(model, path)
        self.failUnless(a[0] in albums)

        albums = StoreUtils.get_albums_for_iter(model, model.get_iter(path))
        self.failUnless(a[0] in albums)

        x = StoreUtils.get_album(model, model.get_iter_root())
        self.failIf(x)
        x = StoreUtils.get_album(model, model.get_iter(path))
        self.failUnlessEqual(x, a[0])

        for r in model:
            self.failUnless(StoreUtils.get_markup(model, model.tags, r.iter))
add(TCollectionAlbums)
