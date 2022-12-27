# Copyright 2022 Felix Krull
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
from textwrap import dedent

from quodlibet.formats import AudioFile

from tests.plugin import PluginTestCase
from tests.helper import temp_filename


class TPlaylistExport(PluginTestCase):
    def setUp(self):
        self.mod = self.modules["Playlist Export"]

    def test_m3u_playlist(self):
        plugin = self.mod.PlaylistExport()
        song1 = AudioFile(
            {
                "~filename": "/a/b/c.mp3",
                "~#length": 123,
                "artist": "a",
                "title": "c",
            }
        )
        song2 = AudioFile(
            {
                "~filename": "/a/b/d.mp3",
                "~#length": 400,
                "artist": "b",
                "title": "d",
            }
        )

        with temp_filename() as playlist_file_path:
            plugin.save_playlist(
                [song1, song2], playlist_file_path, self.mod.FORMAT_M3U, relative=False
            )
            with open(playlist_file_path, "r") as f:
                result = f.read()

        self.assertEqual(
            result,
            dedent(
                """\
            #EXTM3U
            #EXTINF:123,a - c
            /a/b/c.mp3
            #EXTINF:400,b - d
            /a/b/d.mp3
            """
            ),
        )

    def test_m3u_playlist_relative(self):
        plugin = self.mod.PlaylistExport()
        with temp_filename() as playlist_file_path:
            d = os.path.dirname(playlist_file_path)
            pd = os.path.dirname(d)
            song1 = audio_file(
                filename=os.path.join(d, "a", "b.mp3"), length=23, artist="a", title="b"
            )
            song2 = audio_file(
                filename=os.path.join(pd, "c.mp3"),
                length=1,
                artist="a",
                title="c",
            )

            plugin.save_playlist(
                [song1, song2], playlist_file_path, self.mod.FORMAT_M3U, relative=True
            )
            with open(playlist_file_path, "r") as f:
                result = f.read()

        self.assertEqual(
            result,
            dedent(
                f"""\
            #EXTM3U
            #EXTINF:23,a - b
            {os.path.join("a", "b.mp3")}
            #EXTINF:1,a - c
            {os.path.join(os.pardir, "c.mp3")}
            """
            ),
        )

    def test_pls_playlist(self):
        plugin = self.mod.PlaylistExport()
        song1 = audio_file(filename="/a/b/c.mp3", length=123, artist="a", title="c")
        song2 = audio_file(filename="/a/b/d.mp3", length=400, artist="b", title="d")

        with temp_filename() as playlist_file_path:
            plugin.save_playlist(
                [song1, song2], playlist_file_path, self.mod.FORMAT_PLS, relative=False
            )
            with open(playlist_file_path, "r") as f:
                result = f.read()

        self.assertEqual(
            result,
            dedent(
                """\
            [playlist]
            File1=/a/b/c.mp3
            Title1=a - c
            Length1=123
            File2=/a/b/d.mp3
            Title2=b - d
            Length2=400
            NumberOfEntries=2
            Version=2
            """
            ),
        )

    def test_pls_playlist_relative(self):
        plugin = self.mod.PlaylistExport()
        with temp_filename() as playlist_file_path:
            d = os.path.dirname(playlist_file_path)
            pd = os.path.dirname(d)
            song1 = audio_file(
                filename=os.path.join(d, "a", "b.mp3"), length=23, artist="a", title="b"
            )
            song2 = audio_file(
                filename=os.path.join(pd, "c.mp3"),
                length=1,
                artist="a",
                title="c",
            )

            plugin.save_playlist(
                [song1, song2], playlist_file_path, self.mod.FORMAT_PLS, relative=True
            )
            with open(playlist_file_path, "r") as f:
                result = f.read()

        self.assertEqual(
            result,
            dedent(
                f"""\
            [playlist]
            File1={os.path.join("a", "b.mp3")}
            Title1=a - b
            Length1=23
            File2={os.path.join(os.pardir, "c.mp3")}
            Title2=a - c
            Length2=1
            NumberOfEntries=2
            Version=2
            """
            ),
        )

    def test_m3u_relative_path_starting_with_octothorpe(self):
        plugin = self.mod.PlaylistExport()
        with temp_filename() as playlist_file_path:
            d = os.path.dirname(playlist_file_path)
            song = audio_file(
                filename=os.path.join(d, "#file.mp3"), length=1, artist="a", title="b"
            )

            plugin.save_playlist(
                [song], playlist_file_path, self.mod.FORMAT_M3U, relative=True
            )
            with open(playlist_file_path, "r") as f:
                result = f.read()

        self.assertEqual(
            result,
            dedent(
                f"""\
            #EXTM3U
            #EXTINF:1,a - b
            {os.path.join(os.curdir, "#file.mp3")}
            """
            ),
        )


def audio_file(filename, length, artist, title):
    return AudioFile(
        {
            "~filename": filename,
            "~#length": length,
            "artist": artist,
            "title": title,
        }
    )
