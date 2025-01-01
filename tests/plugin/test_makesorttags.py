# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet.ext.songsmenu.makesorttags import album_to_sort, artist_to_sort
from quodlibet.formats import AudioFile
from quodlibet.util.songwrapper import SongWrapper
from tests.plugin import PluginTestCase


class TMakeSortTags(PluginTestCase):
    def setUp(self):
        globals().update(vars(self.modules["SortTags"]))
        self.kind = self.plugins["SortTags"].cls

    def test_util_functions(self):
        assert artist_to_sort("artist", "The Strokes") == "Strokes, The"
        assert album_to_sort("The Very Greatest Hits") == "Very Greatest Hits, The"

    def test_multi_word(self):
        assert artist_to_sort("artist", "The Beach Boys") == "Beach Boys, The"
        performer = artist_to_sort("performer", "The Notorious B.I.G.")
        assert performer == "Notorious B.I.G., The"
        # Debatable...
        assert artist_to_sort("artist", "Echo and the Bunnymen") is None
        # ...but the debate ended for me after seeing "Machine, Rage Against The" :)
        assert artist_to_sort("artist", "Rage Against The Machine") is None
        assert artist_to_sort("artist", "Guns 'n' Roses") is None
        assert artist_to_sort("albumartist", "Everything But The Girl") is None

        assert album_to_sort("The Very Greatest Hits") == "Very Greatest Hits, The"

    def test_no_blanks(self):
        s = AudioFile({"filename": "/dev/null", "artist": "The Beatles"})
        sw = SongWrapper(s)
        self.plugin = self.kind([sw], None).plugin_song(sw)
        assert sw("artistsort") == "Beatles, The"
        assert "performersort" not in sw._song
        assert "albumartistsort" not in sw._song
        assert "albumsort" not in sw._song

    def test_composer(self):
        s = AudioFile({"filename": "/dev/null", "composer": "J.S. Bach"})
        sw = SongWrapper(s)
        self.plugin = self.kind([sw], None).plugin_song(sw)
        assert sw("composersort") == "Bach, J.S."

    def test_composer_artist(self):
        s = AudioFile({"filename": "/dev/null", "artist": "Gabriel Fauré"})
        sw = SongWrapper(s)
        self.plugin = self.kind([sw], None).plugin_song(sw)
        assert sw("artistsort") == "Fauré, Gabriel"
