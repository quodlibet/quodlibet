# -*- coding: utf-8 -*-
# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import mutagen

from quodlibet.compat import cBytesIO
from tests import TestCase, get_data_path
from quodlibet.formats.mp4 import MP4File
from quodlibet.formats._image import EmbeddedImage

import mutagen.mp4

from .helper import get_temp_copy


class TMP4File(TestCase):

    def setUp(self):
        self.f = get_temp_copy(get_data_path('test.m4a'))
        self.song = MP4File(self.f)

    def tearDown(self):
        os.unlink(self.f)

    def _assert_tag_supported(self, tag, value="SomeTestValue"):
        self.song[tag] = value
        self.song.write()
        self.song.reload()
        self.assertEqual(self.song(tag), value)

    def test_format(self):
        self.assertEqual(self.song("~format"), "MPEG-4")

    def test_codec(self):
        self.assertEqual(self.song("~codec"), "AAC LC")

    def test_encoding(self):
        self.assertEqual(self.song("~encoding"), "FAAC 1.24")

    def test_mb_release_track_id(self):
        tag = mutagen.mp4.MP4(self.f)
        tag["----:com.apple.iTunes:MusicBrainz Release Track Id"] = [b"foo"]
        tag.save()
        song = MP4File(self.f)
        self.assertEqual(song("musicbrainz_releasetrackid"), u"foo")
        song["musicbrainz_releasetrackid"] = u"bla"
        song.write()
        tag = mutagen.mp4.MP4(self.f)
        self.assertEqual(
            tag["----:com.apple.iTunes:MusicBrainz Release Track Id"],
            [b"bla"])

    def test_basic(self):
        self._assert_tag_supported("title")
        self._assert_tag_supported("artist")
        self._assert_tag_supported("albumartist")
        self._assert_tag_supported("album")
        self._assert_tag_supported("genre")
        self._assert_tag_supported("date")

    def test_basic_numeric(self):
        self._assert_tag_supported("tracknumber", "12")
        self._assert_tag_supported("discnumber", "1")
        self._assert_tag_supported("bpm", "132")

    def test_less_common_tags(self):
        self._assert_tag_supported("discsubtitle")
        self._assert_tag_supported("mood")
        self._assert_tag_supported("conductor")

    def test_replaygain_tags(self):
        self._assert_tag_supported('replaygain_album_gain', '-5.67 dB')
        self._assert_tag_supported('replaygain_album_peak', '1.0')
        self._assert_tag_supported('replaygain_track_gain', '-5.67 dB')
        self._assert_tag_supported('replaygain_track_peak', '1.0')
        self._assert_tag_supported('replaygain_reference_loudness', '89 dB')

    def test_length(self):
        self.assertAlmostEqual(self.song("~#length"), 3.7079, 3)

    def test_bitrate(self):
        self.assertEqual(self.song("~#bitrate"), 2)

    def test_channels(self):
        assert self.song("~#channels") == 2

    def test_samplerate(self):
        assert self.song("~#samplerate") == 44100

    def test_bitdepth(self):
        assert self.song("~#bitdepth") == 16

    def test_bpm_rounds(self):
        self.song["bpm"] = "98.76"
        self.song.write()
        self.song.reload()
        self.assertEqual(self.song("bpm"), "99")
        self.assertEqual(self.song("~#bpm"), 99)

    def test_empty_disk_trkn(self):
        for key in ["trkn", "disk"]:
            tag = mutagen.mp4.MP4(self.f)
            tag[key] = []
            tag.save()
            tag = mutagen.mp4.MP4(self.f)
            assert tag[key] == []
            self.song.reload()

    def test_write(self):
        self.song.write()

    def test_can_change(self):
        self.assertTrue(self.song.can_change("title"))
        self.assertFalse(self.song.can_change("foobar"))
        self.assertTrue("albumartist" in self.song.can_change())

    def test_invalid(self):
        path = get_data_path('empty.xm')
        self.assertTrue(os.path.exists(path))
        self.assertRaises(Exception, MP4File, path)

    def test_get_image(self):
        image = self.song.get_primary_image()
        self.assertTrue(image)
        self.assertEqual(image.mime_type, "image/png")

    def test_get_images(self):
        images = self.song.get_images()
        self.assertTrue(images and len(images) == 2)

    def test_get_image_non(self):
        tag = mutagen.mp4.MP4(self.f)
        tag.pop("covr", None)
        tag.save()
        self.song.reload()

        self.assertFalse(self.song.get_primary_image())

    def test_clear_images(self):
        self.assertTrue(self.song.valid())
        self.assertTrue(self.song.has_images)
        self.song.clear_images()
        self.assertFalse(self.song.has_images)
        self.assertFalse(self.song.get_primary_image())

        tag = mutagen.mp4.MP4(self.f)
        self.assertFalse("covr" in tag)

    def test_set_image(self):
        self.assertTrue(self.song.has_images)
        fileobj = cBytesIO(b"foo")
        image = EmbeddedImage(fileobj, "image/jpeg", 10, 10, 8)
        self.song.set_image(image)
        image = self.song.get_primary_image()
        self.assertTrue(image)
        self.assertEqual(image.read(), b"foo")
        self.assertTrue(self.song.has_images)

    def test_can_change_images(self):
        self.assertTrue(self.song.can_change_images)

    def test_can_multiple_values(self):
        self.assertEqual(self.song.can_multiple_values(), [])
        self.assertFalse(self.song.can_multiple_values("artist"))
