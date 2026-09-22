# Copyright 2012,2014 Christoph Reiter
#                2016 Nick Boultbee
#                2019 Ruud van Asseldonk
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


from quodlibet.browsers.covergrid.main import CoverGrid

from . import TestCase, run_gtk_loop
from .helper import realized

from quodlibet import config

from quodlibet.browsers.albums.prefs import DEFAULT_PATTERN_TEXT
from quodlibet.formats import AudioFile
from quodlibet.library import SongLibrary, SongLibrarian


SONGS = [
    AudioFile(
        {
            "album": "one",
            "artist": "piman",
            "~filename": "/dev/null",
        }
    ),
    AudioFile(
        {
            "album": "two",
            "artist": "mu",
            "~filename": "/dev/zero",
        }
    ),
    AudioFile(
        {
            "album": "three",
            "artist": "boris",
            "~filename": "/bin/ls",
        }
    ),
    AudioFile(
        {
            "album": "three",
            "artist": "boris",
            "~filename": "/bin/ls2",
        }
    ),
]
SONGS.sort()


class TCoverGridBrowser(TestCase):
    def setUp(self):
        config.init()

        library = SongLibrary()
        library.librarian = SongLibrarian()
        CoverGrid.init(library)

        for af in SONGS:
            af.sanitize()
        library.add(SONGS)

        self.library = library
        self.bar = CoverGrid(library)

        self._id = self.bar.connect("songs-selected", self._selected)
        self._id2 = self.bar.connect("songs-activated", self._activated)
        with realized(self.bar):
            self.bar.filter_text("")
            self._wait()
        self.songs = []
        self.activated = False

    def tearDown(self):
        self.bar.disconnect(self._id)
        self.bar.disconnect(self._id2)
        self.bar.destroy()
        del self.bar
        config.quit()

    def _activated(self, albumlist):
        self.activated = True

    def _selected(self, albumlist, songs, *args):
        self.songs = songs

    def _wait(self):
        run_gtk_loop()

    def test_activated(self):
        with realized(self.bar):
            view = self.bar.view
            child = view.get_child_at_index(0)
            child.emit("activate")
            self._wait()
            assert self.activated

    def test_can_filter(self):
        with realized(self.bar):
            assert self.bar.can_filter(None)
            assert self.bar.can_filter("album")
            assert self.bar.can_filter("foobar")
            assert not self.bar.can_filter("~#length")
            assert not self.bar.can_filter("title")

    def test_set_text(self):
        with realized(self.bar):
            self.bar.filter_text("artist=piman")
            self._wait()
            self.assertEqual(len(self.songs), 1)
            self.bar.filter_text("")
            self._wait()
            self.assertEqual(set(self.songs), set(SONGS))

    def test_filter_album(self):
        with realized(self.bar):
            self.bar.filter_text("dsagfsag")
            self._wait()
            self.assertEqual(len(self.songs), 0)
            self.bar.filter_text("")
            self._wait()
            self.bar.filter("album", ["one", "three"])
            self._wait()
            self.assertEqual(len(self.songs), 3)

    def test_filter_artist(self):
        with realized(self.bar):
            self.bar.filter("artist", ["piman"])
            self._wait()
            self.assertEqual(len(self.songs), 1)
            self.assertEqual(self.songs[0]("artist"), "piman")

    def test_header(self):
        assert not self.bar.headers

    def test_list(self):
        albums = self.bar.list_albums()
        self.assertEqual(set(albums), {s.album_key for s in SONGS})
        self.bar.filter_albums([SONGS[0].album_key])
        self._wait()
        self.assertEqual({s.album_key for s in self.songs}, {SONGS[0].album_key})

    def test_active_filter(self):
        with realized(self.bar):
            self.bar.filter("artist", ["piman"])
            self._wait()
            assert self.bar.active_filter(self.songs[0])
            for s in SONGS:
                if s is not self.songs[0]:
                    assert not self.bar.active_filter(s)

    def test_default_display_pattern(self):
        pattern_text = self.bar.display_pattern_text
        self.assertEqual(pattern_text, DEFAULT_PATTERN_TEXT)
        assert "<album>" in pattern_text

    def _songs_for(self, artists):
        if artists is None:
            return set(SONGS)
        return {song for song in SONGS if song("artist") in artists}

    def _album_keys_for(self, artists):
        return {song.album_key for song in self._songs_for(artists)}

    def _filter_model(self, browser):
        # Album membership and the All Albums count live on the filter model.
        # FlowBox children are not required for that, and GTK can report a
        # filter exception without failing the caller.
        return browser._CoverGrid__model_filter

    def _visible_keys(self, browser):
        return set(browser.list_albums())

    def _assert_albums(self, browser, artists, songs):
        expected_songs = self._songs_for(artists)
        expected_keys = self._album_keys_for(artists)
        self.assertEqual(self._visible_keys(browser), expected_keys)
        self.assertEqual(set(songs), expected_songs)
        self._assert_all_albums(browser, len(expected_keys))

    def _assert_all_albums(self, browser, count):
        model = self._filter_model(browser)
        items = [model[i] for i in range(len(model))]
        assert items
        sentinel = items[0]
        assert sentinel.album is None
        self.assertEqual(sentinel.props.n_albums, count)
        visible = [item for item in items if item.album is not None]
        self.assertEqual(len(visible), count)
        self.assertEqual(len(items), count + 1)

        index = 0
        while True:
            child = browser.view.get_child_at_index(index)
            if child is None:
                break
            assert child.get_visible()
            if index == 0:
                assert child.model.album is None
                self.assertEqual(child.model.props.n_albums, count)
            index += 1
        self.assertEqual(index, count + 1)

    def _apply_search(self, browser, text):
        with realized(browser):
            browser.filter_text(text)
            self._wait()

    def test_empty_search_applies_global_filter(self):
        # Include an album the background predicate accepts. A predicate that
        # rejects every album would short-circuit before calling the absent
        # search and hide the original TypeError.
        config.settext("browsers", "background", "|(artist=piman,artist=boris)")
        self._apply_search(self.bar, "")
        self._assert_albums(self.bar, {"piman", "boris"}, self.songs)

    def test_search_intersects_global_filter_then_clear(self):
        config.settext("browsers", "background", "|(artist=piman,artist=boris)")
        with realized(self.bar):
            self.bar.filter_text("artist=piman")
            self._wait()
            self._assert_albums(self.bar, {"piman"}, self.songs)

            # Search matches an album the global filter rejects.
            # An empty selection does not emit songs-selected again, so
            # membership and the All Albums count are the observable result.
            self.bar.filter_text("artist=mu")
            self._wait()
            self.assertEqual(self._visible_keys(self.bar), set())
            self._assert_all_albums(self.bar, 0)

            self.bar.filter_text("")
            self._wait()
            self._assert_albums(self.bar, {"piman", "boris"}, self.songs)

    def test_filter_predicate_combinations(self):
        with realized(self.bar):
            # Absent background, absent search.
            self.bar.filter_text("")
            self._wait()
            self._assert_albums(self.bar, None, self.songs)

            # Absent background, present search.
            self.bar.filter_text("artist=piman")
            self._wait()
            self._assert_albums(self.bar, {"piman"}, self.songs)

            # Present background, absent search.
            config.settext("browsers", "background", "|(artist=piman,artist=boris)")
            self.bar.filter_text("")
            self._wait()
            self._assert_albums(self.bar, {"piman", "boris"}, self.songs)

            # Present background, present search.
            self.bar.filter_text("artist=boris")
            self._wait()
            self._assert_albums(self.bar, {"boris"}, self.songs)

            # Removing the background filter restores every album on an empty
            # search, and search-only filtering still applies.
            config.settext("browsers", "background", "")
            self.bar.filter_text("")
            self._wait()
            self._assert_albums(self.bar, None, self.songs)

            self.bar.filter_text("artist=mu")
            self._wait()
            self._assert_albums(self.bar, {"mu"}, self.songs)

    def test_all_albums_sentinel_counts_filtered_set(self):
        config.settext("browsers", "background", "|(artist=piman,artist=boris)")
        with realized(self.bar):
            self.bar.filter_text("")
            self._wait()
            self._assert_all_albums(self.bar, 2)
            self.assertEqual(len(self.songs), 3)

            config.settext("browsers", "background", "artist=nobody")
            self.bar.filter_text("")
            self._wait()
            self.assertEqual(self._visible_keys(self.bar), set())
            self._assert_all_albums(self.bar, 0)

            config.settext("browsers", "background", "|(artist=piman,artist=boris)")
            self.bar.filter_text("artist=nobody")
            self._wait()
            self.assertEqual(self._visible_keys(self.bar), set())
            self._assert_all_albums(self.bar, 0)

    def test_startup_empty_search_applies_global_filter(self):
        config.settext("browsers", "background", "|(artist=piman,artist=boris)")
        selected = []

        def on_selected(_browser, songs, *_args):
            selected[:] = songs

        browser = CoverGrid(self.library)
        browser.connect("songs-selected", on_selected)
        try:
            # Construction applies the initial empty search.
            self.assertEqual(
                set(browser.list_albums()), self._album_keys_for({"piman", "boris"})
            )
            self._assert_all_albums(browser, 2)
            with realized(browser):
                browser.filter_text("")
                self._wait()
            self._assert_albums(browser, {"piman", "boris"}, selected)
        finally:
            browser.destroy()
