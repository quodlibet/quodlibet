# Copyright 2020 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from pathlib import Path
from tempfile import TemporaryDirectory

from quodlibet import config
from quodlibet.formats import AudioFile
from tests.plugin import PluginTestCase


class TSynchronizedlyrics(PluginTestCase):
    AN_LRC = """
    [ti:Test Thing]
    [length:66:66.66]
    [01:23.45] This is some text
    [01:01.00]Starting here?
    [61:00.00]Past the hour mark now!
    """
    EXPECTED_LYRICS = [
        (1000 * 61, "Starting here?"),
        (1000 * (60 + 23.45), "This is some text"),
        (1000 * 61.0 * 60, "Past the hour mark now!"),
    ]

    def setUp(self):
        self.mod = self.modules["SynchronizedLyrics"]
        self.plugin = self.mod.SynchronizedLyrics()

    def tearDown(self):
        config.quit()

    def test_empty_parsing(self):
        assert self.plugin._parse_lrc("") == []

    def test_lrc_parsing(self):
        assert self.plugin._parse_lrc(self.AN_LRC) == self.EXPECTED_LYRICS

    def test_build_data_for_no_song(self):
        assert self.plugin._build_data(None) == []

    def test_build_data_for_munged_name(self):
        with TemporaryDirectory() as dir_:
            song = AudioFile(
                {
                    "~filename": f"{dir_}/ARTIST - TITLE.mp3",
                    "artist": "ARTIST",
                    "title": "TITLE",
                }
            )
            path = Path(dir_) / f"{song('artist')} - {song('title')}.lrc"
            with open(path, "w") as f:
                f.write(self.AN_LRC)
            assert self.plugin._build_data(song) == self.EXPECTED_LYRICS

    def test_build_data_for_embedded_lyrics(self):
        with TemporaryDirectory() as dir_:
            song = AudioFile(
                {
                    "~filename": f"{dir_}/ARTIST - TITLE.mp3",
                    "artist": "ARTIST",
                    "title": "TITLE",
                    "lyrics": self.AN_LRC,
                }
            )
            data = self.plugin._build_data(song)
            assert data == self.EXPECTED_LYRICS
