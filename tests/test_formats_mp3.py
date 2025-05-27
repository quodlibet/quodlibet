# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
import random
import shutil
import time
from pathlib import Path

import pytest

from quodlibet.formats.mp3 import MP3File
from tests import TestCase, get_data_path, mkstemp


class TMP3File(TestCase):
    def setUp(self):
        self.song = MP3File(get_data_path("silence-44-s.mp3"))
        self.song2 = MP3File(get_data_path("test.mp2"))
        self.song3 = MP3File(get_data_path("lame.mp3"))

    def test_channels(self):
        assert self.song("~#channels") == 2
        assert self.song2("~#channels") == 1
        assert self.song3("~#channels") == 2

    def test_samplerate(self):
        assert self.song("~#samplerate") == 44100
        assert self.song2("~#samplerate") == 32000
        assert self.song3("~#samplerate") == 44100

    def test_length(self):
        self.assertAlmostEqual(self.song("~#length"), 3.77, 2)
        self.assertAlmostEqual(self.song2("~#length"), 1.764, 3)
        self.assertAlmostEqual(self.song3("~#length"), 0.0616, 3)

    def test_bitrate(self):
        self.assertEqual(self.song("~#bitrate"), 32)
        self.assertEqual(self.song2("~#bitrate"), 32)
        # 127 with mutagen 1.39+
        assert self.song3("~#bitrate") in [127, 270]

    def test_format(self):
        self.assertEqual(self.song("~format"), "MP3")
        self.assertEqual(self.song2("~format"), "MP2")
        self.assertEqual(self.song3("~format"), "MP3")

    def test_codec(self):
        self.assertEqual(self.song("~codec"), "MP3")
        self.assertEqual(self.song2("~codec"), "MP2")
        self.assertEqual(self.song3("~codec"), "MP3")

    def test_encoding(self):
        self.assertEqual(self.song("~encoding"), "")
        self.assertEqual(self.song2("~encoding"), "")
        assert self.song3("~encoding") in [
            "LAME 3.99.1+\nVBR",
            "LAME 3.99.1+\nVBR\n-V 2",
        ]


@pytest.mark.skip("Enable this for perf testing")
def test_mp3_load_performance():
    t = time.monotonic_ns()
    path = Path(mkstemp(suffix=".mp3")[1])
    shutil.copy(get_data_path("silence-44-s.mp3"), path)
    mp3 = MP3File(str(path))
    data = {
        "title": f"Track #{random.randint(1000, 1000000)}",
        "artist": "Some Artist",
        "albumartist": "Some Other Artist",
        "musicbrainz_albumid": "album123",
        "musicbrainz_trackid": "track123",
        "replaygain_track_gain": f"{random.random()} dB",
        "replaygain_track_peak": f"{random.random()}",
        "replaygain_album_gain": f"{random.random()} dB",
        "replaygain_album_peak": f"{random.random()}",
        "comment": "Blah blah blah\nBlah blah blah",
        "genre": random.choice(["Jazz", "Blues", "Rock", "Classical"]),
        "~#rating": 0.333,
        "~#playcount": 42,
    }

    for key, value in data.items():
        mp3.add(key, value)
    mp3.write()

    assert mp3("~#rating") == 0.333
    total = 10_000
    for i in range(total):
        MP3File(str(path))

    duration_micros = (time.monotonic_ns() - t) / 1000.0
    # Adjust down for testing.
    assert duration_micros / total < 2000, "scarily slow?"

    # Python 3.12 on my Linux x86_64 machine
    # Before: best of 3 = 760µs
    # After:  best of 3 = 749µs
    # Improvement ~= 1.4%
