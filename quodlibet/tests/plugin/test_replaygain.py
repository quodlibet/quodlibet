# Copyright 2014 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

import os

from gi.repository import Gtk
import re
import time
from quodlibet.ext.songsmenu.replaygain import UpdateMode
from quodlibet.formats import MusicFile
from quodlibet.formats._audio import AudioFile

from tests.plugin import PluginTestCase
from tests import DATA_DIR
from quodlibet import config

# Give up analysis after 5s, in case GStreamer (or something else) dies.
TIMEOUT = 5
SONG = AudioFile({'artist': 'foo', 'album': 'the album'})


class TReplayGain(PluginTestCase):
    # Ugh. Store test results statically
    analysed = None

    @classmethod
    def setUpClass(cls):
        config.init()

        cls.mod = cls.modules["ReplayGain"]
        Kind = cls.plugins["ReplayGain"].cls
        cls.songs = []
        cls.plugin = Kind(cls.songs, None, None)

    @classmethod
    def tearDownClass(cls):
        config.quit()
        del cls.mod

    def test_RGSong_properties(self):
        rgs = self.mod.RGSong(SONG)
        self.failIf(rgs.has_album_tags)
        self.failIf(rgs.has_track_tags)
        self.failIf(rgs.has_all_rg_tags)

        rgs.done = True
        rgs._write(-1.23, 0.99)
        self.failUnless(rgs.has_album_tags, msg="Didn't write album tags")
        self.failIf(rgs.has_track_tags)
        self.failIf(rgs.has_all_rg_tags)

    def test_RGSong_zero(self):
        rgs = self.mod.RGSong(SONG)
        rgs.done = True
        rgs._write(0.0, 0.0)
        self.failUnless(rgs.has_album_tags,
                        msg="Failed with 0.0 album tags (%s)" % rgs)

    def test_RGAlbum_properties(self):
        rga = self.mod.RGAlbum([self.mod.RGSong(SONG)], UpdateMode.ALWAYS)
        self.failIf(rga.done)
        self.failUnlessEqual(rga.title, 'foo - the album')

    def _analyse_song(self, song):
        mode = self.mod.UpdateMode.ALWAYS
        self.album = album = self.mod.RGAlbum.from_songs([song], mode)
        self.analysed = None

        def _run_main_loop():
            def on_complete(self, album):
                album.write()
                TReplayGain.analysed = [album]

            pipeline = self.mod.ReplayGainPipeline()
            sig = pipeline.connect('done', on_complete)

            pipeline.start(album)
            start = time.time()
            while not self.analysed and time.time() - start < TIMEOUT:
                Gtk.main_iteration_do(False)
            pipeline.quit()
            pipeline.disconnect(sig)

        _run_main_loop()
        self.assertTrue("Timed out", self.analysed)

    def test_analyze_sinewave(self):
        song = MusicFile(os.path.join(DATA_DIR, "sine-110hz.flac"))
        self.failUnlessEqual(song("~#length"), 2)
        self.failIf(song("~replaygain_track_gain"))

        self._analyse_song(song)

        self.failUnlessAlmostEqual(song("~#replaygain_track_peak"), 1.0,
                                   msg="Track peak should be 1.0")

        track_gain = song("~#replaygain_track_gain")
        self.failUnless(track_gain, msg="No Track Gain added")
        self.failUnless(re.match(r'\-[0-9]\.[0-9]{1,2}', str(track_gain)))

        # For one-song album, track == album
        self.failUnlessEqual(track_gain, song('~#replaygain_album_gain'))

    def test_analyze_silence(self):
        song = MusicFile(os.path.join(DATA_DIR, "silence-44-s.ogg"))
        self.failIf(song("~replaygain_track_gain"))

        self._analyse_song(song)

        self.failUnlessAlmostEqual(song("~#replaygain_track_peak"), 0.0,
                                   msg="Track peak should be 0.0")

        track_gain = song("~#replaygain_track_gain")
        self.failUnless(track_gain, msg="No Track Gain added")

        # For one-song album, track == album
        self.failUnlessEqual(track_gain, song('~#replaygain_album_gain'))
