# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

from quodlibet import config

from quodlibet.browsers.collection import CollectionBrowser
from quodlibet.browsers.collection.models import (
    UnknownNode,
    CollectionTreeStore,
    build_tree,
    MultiNode,
)
from quodlibet.browsers.collection.prefs import save_headers, get_headers, PatternEditor
from quodlibet.formats import AudioFile
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
        self.assertEqual(get_headers(), value)

    def test_pref_dialog(self):
        d = PatternEditor()
        d.destroy()


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
        assert "mu" in tree
        assert "boris" in tree
        assert "piman" in tree
        assert UnknownNode in tree
        self.assertEqual(len(tree), 4)

    def test_build_tree_merge(self):
        tags = [("~people", 1)]
        tree = build_tree(tags, self.albums)
        assert MultiNode in tree
        assert UnknownNode in tree
        assert "boris" in tree
        assert "piman" in tree
        self.assertEqual(len(tree), 4)

    def test_model(self):
        model = CollectionTreeStore()
        model.set_albums([("~people", 0)], self.albums)
        self.assertEqual(len(model), 4)
        model.change_albums(self.albums)
        self.assertEqual(len(model), 4)
        model.remove_albums(self.albums)
        self.assertEqual(len(model), 0)

    def test_utils(self):
        model = CollectionTreeStore()
        model.set_albums([("~people", 0)], self.albums)
        a = list(self.albums.values())
        a.sort(key=lambda x: x.key)

        path = model.get_path_for_album(a[0])
        albums = model.get_albums_for_path(path)
        assert a[0] in albums

        albums = model.get_albums_for_iter(model.get_iter(path))
        assert a[0] in albums

        x = model.get_album(model.get_iter_first())
        assert not x
        x = model.get_album(model.get_iter(path))
        self.assertEqual(x, a[0])

        for r in model:
            assert model.get_markup(model.tags, r.iter)

        x = list(model.iter_albums(None))
        self.assertEqual(set(x), set(a))


class TCollectionBrowser(TestCase):
    def setUp(self):
        config.init()

    def tearDown(self):
        config.quit()

    def test_init(self):
        library = SongLibrary()
        x = CollectionBrowser(library)
        x.destroy()
