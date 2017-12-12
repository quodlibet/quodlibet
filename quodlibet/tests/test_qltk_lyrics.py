# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
from senf import fsnative

import quodlibet.config
from quodlibet.formats import AudioFile
from quodlibet.formats.mp3 import MP3File
from quodlibet.library import SongLibrary
from quodlibet.qltk.lyrics import LyricsPane
from tests import TestCase, init_fake_app, destroy_fake_app, get_data_path
from tests.helper import get_temp_copy

LYRICS = "foobär...\nMore cowbell!©"


def AF(*args, **kwargs):
    a = AudioFile(*args, **kwargs)
    a.sanitize()
    return a


class TLyricsPane(TestCase):

    def setUp(self):
        quodlibet.config.init()
        init_fake_app()
        self.pane = None
        self.library = SongLibrary()

    def tearDown(self):
        destroy_fake_app()
        self.library.destroy()
        quodlibet.config.quit()
        if self.pane:
            self.pane.destroy()

    def test_construction(self):
        af = AF({"~filename": fsnative(u"/dev/null")})
        self.pane = LyricsPane(af)

    def test_save_lyrics(self):
        af = self.temp_mp3()
        self.pane = LyricsPane(af)
        self.pane._save_lyrics(af, LYRICS)
        self.failUnlessEqual(af("~lyrics"), LYRICS)

    def test_save_encoded_lyrics(self):
        af = self.temp_mp3()
        self.pane = LyricsPane(af)
        self.pane._save_lyrics(af, LYRICS)
        self.failUnlessEqual(af("~lyrics"), LYRICS)

    def test_save_lyrics_deletes_lyric_file(self):
        af = self.temp_mp3()
        lf_name = af.lyric_filename
        os.makedirs(os.path.dirname(lf_name))
        with open(lf_name, "wb") as f:
            f.write(LYRICS.encode("utf-8"))
        self.failUnless(os.path.exists(lf_name))
        self.pane = LyricsPane(af)
        self.pane._save_lyrics(af, LYRICS)
        self.failIf(os.path.exists(lf_name))

    def temp_mp3(self):
        name = get_temp_copy(get_data_path('silence-44-s.mp3'))
        af = MP3File(name)
        af.sanitize()
        return af
