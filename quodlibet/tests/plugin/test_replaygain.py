# -*- coding: utf-8 -*-
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
from quodlibet.formats import AudioFile

from tests.plugin import PluginTestCase
from tests import DATA_DIR


class TReplayGain(PluginTestCase):

    # Give up analysis after some time, in case GStreamer dies.
    TIMEOUT = 20

    @classmethod
    def setUpClass(cls):
        cls.mod = cls.modules["ReplayGain"]
        cls.kind = cls.plugins["ReplayGain"].cls

    @classmethod
    def tearDownClass(cls):
        del cls.mod
        del cls.kind

    def setUp(self):
        self.song = AudioFile({'artist': 'foo', 'album': 'the album'})
        self.plugin = self.kind([self.song], None)

    def tearDown(self):
        self.plugin.destroy()
        del self.plugin
        del self.song

    def test_RGSong_properties(self):
        rgs = self.mod.RGSong(self.song)
        self.failIf(rgs.has_album_tags)
        self.failIf(rgs.has_track_tags)
        self.failIf(rgs.has_all_rg_tags)

        rgs.done = True
        rgs._write(-1.23, 0.99)
        self.failUnless(rgs.has_album_tags, msg="Didn't write album tags")
        self.failIf(rgs.has_track_tags)
        self.failIf(rgs.has_all_rg_tags)

    def test_RGSong_zero(self):
        rgs = self.mod.RGSong(self.song)
        rgs.done = True
        rgs._write(0.0, 0.0)
        self.failUnless(rgs.has_album_tags,
                        msg="Failed with 0.0 album tags (%s)" % rgs)

    def test_RGAlbum_properties(self):
        rga = self.mod.RGAlbum([self.mod.RGSong(self.song)], UpdateMode.ALWAYS)
        self.failIf(rga.done)
        self.failUnlessEqual(rga.title, 'foo - the album')

    def test_delete_bs1770gain(self):
        tags = ["replaygain_reference_loudness", "replaygain_algorithm",
                "replaygain_album_range", "replaygain_track_range"]

        for tag in tags:
            self.song[tag] = u"foo"

        rgs = self.mod.RGSong(self.song)
        rgs.done = True
        rgs._write(0.0, 0.0)

        for tag in tags:
            self.assertFalse(self.song(tag))

    def _analyse_song(self, song):
        mode = self.mod.UpdateMode.ALWAYS
        self.album = album = self.mod.RGAlbum.from_songs([song], mode)
        self.analysed = None

        def _run_main_loop():
            def on_complete(pipeline, album):
                album.write()
                self.analysed = [album]

            pipeline = self.mod.ReplayGainPipeline()
            sig = pipeline.connect('done', on_complete)

            pipeline.start(album)
            start = time.time()
            while not self.analysed and \
                    abs(time.time() - start) < self.TIMEOUT:
                Gtk.main_iteration_do(False)
            pipeline.quit()
            pipeline.disconnect(sig)

        _run_main_loop()
        self.assertTrue(self.analysed, "Timed out")

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
