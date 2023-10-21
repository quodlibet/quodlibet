# Copyright 2022 TheMelmacian
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
from io import BufferedReader
from urllib.response import addinfourl

from quodlibet.browsers.playlists.util import _dir_for, parse_m3u
from quodlibet.library import SongFileLibrary
from quodlibet.library.playlist import PlaylistLibrary
from quodlibet.util.collection import Playlist
from quodlibet.util.urllib import urlopen
from tests import TestCase, get_data_path


class TPlaylistUtil(TestCase):

    PLAYLIST_FILE_PATH = get_data_path('test.m3u8')
    sfLib: SongFileLibrary = None
    plLib: PlaylistLibrary = None

    def setUp(self):
        self.sfLib = SongFileLibrary()
        self.plLib = PlaylistLibrary(self.sfLib)

    def tearDown(self):
        self.plLib.destroy()
        self.sfLib.destroy()

    def test_dir_for(self):
        # uri format of files added via drag and drop or add button
        # (Gtk.SelectionData.get_uris()): file:///path/to/file.ext
        url_based_file: addinfourl = urlopen("file:///" + self.PLAYLIST_FILE_PATH)
        reader_based_file: BufferedReader = open(self.PLAYLIST_FILE_PATH, "rb")

        try:
            dir_of_url_based_file: str = _dir_for(url_based_file)
            self.assertEqual(
                os.path.realpath(os.path.dirname(self.PLAYLIST_FILE_PATH)),
                os.path.realpath(dir_of_url_based_file),
                "determining the directory of url based files"
                " should result in a correct path"
            )

            dir_of_reader_based_file: str = _dir_for(reader_based_file)
            self.assertEqual(
                os.path.realpath(os.path.dirname(self.PLAYLIST_FILE_PATH)),
                os.path.realpath(dir_of_reader_based_file,),
                "determining the directory of reader based files"
                " should result in a correct path"
            )

        finally:
            url_based_file.close()
            reader_based_file.close()

    def test_parse_m3u8(self):
        fileName = os.path.basename(self.PLAYLIST_FILE_PATH)
        playlist: Playlist = None

        with open(self.PLAYLIST_FILE_PATH, "rb") as file:
            try:
                playlist = parse_m3u(file, fileName, self.sfLib, self.plLib)
            except Exception:
                assert False, ("parsing m3u8 playlists in correct format"
                               " should not cause errors")

        self.assertIsNotNone(playlist, ("parsing an m3u8 playlist in the correct format"
                                        " should result in a playlist"))
        # the test.m3u8 contains:
        #   - 3 existing and supported audio files from the tests/data folder:
        #     lame.mp3, test.wav, sine-110hz.flac
        #   - 1 non existing file: non_existing_audio_file.mp3
        #   - 1 not supported file: test.jpg
        # parsing the file correctly should result in a playlist with 3 entries
        self.assertEqual(
            3,
            len(playlist),
            "only existing files should be added to the playlist"
        )
