# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
from io import BytesIO

from mutagen import asf

from tests import TestCase, get_data_path
from quodlibet.formats.wma import WMAFile, unpack_image, pack_image
from quodlibet.formats._image import APICType, EmbeddedImage

from .helper import get_temp_copy


class TWMAFile(TestCase):

    def setUp(self):
        self.f = get_temp_copy(get_data_path('test.wma'))
        self.song = WMAFile(self.f)

        self.f2 = get_temp_copy(get_data_path('test-2.wma'))
        self.song2 = WMAFile(self.f2)

        self.f3 = get_temp_copy(get_data_path('test.asf'))
        self.song3 = WMAFile(self.f3)

    def tearDown(self):
        os.unlink(self.f)
        os.unlink(self.f2)
        os.unlink(self.f3)

    def test_basic(self):
        self.song["title"] = u"SomeTestValue"
        self.song.write()
        self.song.reload()
        self.assertEqual(self.song("title"), u"SomeTestValue")

    def test_multi(self):
        self.song["genre"] = u"Rock\nPop"
        self.song.write()
        self.song.reload()
        # XXX: mutagen doesn't preserve order.. fix it!
        self.assertEqual(set(self.song.list("genre")), {u"Rock", u"Pop"})

    def test_length(self):
        self.assertAlmostEqual(self.song("~#length"), 3.7120, 3)
        self.assertAlmostEqual(self.song2("~#length"), 3.684, 3)
        self.assertAlmostEqual(self.song3("~#length"), 11.38, 2)

    def test_channels(self):
        assert self.song("~#channels") == 2
        assert self.song2("~#channels") == 2
        assert self.song3("~#channels") == 1

    def test_bitrate(self):
        self.assertEqual(self.song("~#bitrate"), 64)
        self.assertEqual(self.song2("~#bitrate"), 38)
        self.assertEqual(self.song3("~#bitrate"), 5)

    def test_sample_rate(self):
        assert self.song("~#samplerate") == 48000
        assert self.song2("~#samplerate") == 44100
        assert self.song3("~#samplerate") == 8000

    def test_write(self):
        self.song.write()
        self.song2.write()
        self.song3.write()

    def test_can_change(self):
        self.assertTrue(self.song.can_change("title"))
        self.assertFalse(self.song.can_change("foobar"))
        self.assertTrue("albumartist" in self.song.can_change())

    def test_format(self):
        self.assertEqual(self.song("~format"), "ASF")
        self.assertEqual(self.song2("~format"), "ASF")
        self.assertEqual(self.song3("~format"), "ASF")

    def test_codec(self):
        self.assertEqual(self.song("~codec"),
                         u"Windows Media Audio 9 Standard")
        self.assertEqual(self.song2("~codec"),
                         u"Windows Media Audio 9 Professional")
        self.assertEqual(self.song3("~codec"),
                         u"Intel G.723")

    def test_encoding(self):
        self.assertEqual(
            self.song("~encoding"),
            u"Windows Media Audio 9.1\n64 kbps, 48 kHz, stereo 2-pass CBR")
        self.assertEqual(
            self.song2("~encoding"),
            (u"Windows Media Audio 9.1 Professional\n192 kbps, 44 kHz, "
             "2 channel 24 bit 2-pass VBR"))
        self.assertEqual(self.song3("~encoding"),
                         u"Microsoft G.723.1\n8 kHz Mono, 5333 Bit/s")

    def test_mb_release_track_id(self):
        tag = asf.ASF(self.f)
        tag["MusicBrainz/Release Track Id"] = [u"foo"]
        tag.save()
        song = WMAFile(self.f)
        self.assertEqual(song("musicbrainz_releasetrackid"), u"foo")
        song["musicbrainz_releasetrackid"] = u"bla"
        song.write()
        tag = asf.ASF(self.f)
        self.assertEqual(tag["MusicBrainz/Release Track Id"], [u"bla"])

    def test_invalid(self):
        path = get_data_path('empty.xm')
        self.assertTrue(os.path.exists(path))
        self.assertRaises(Exception, WMAFile, path)

    def test_get_images(self):
        tag = asf.ASF(self.f2)
        tag["WM/Picture"] = [tag["WM/Picture"][0], tag["WM/Picture"][0]]
        tag.save()
        self.song2.reload()

        images = self.song2.get_images()
        self.assertTrue(images and len(images) == 2)

    def test_get_image(self):
        self.assertFalse(self.song.get_primary_image())

        image = self.song2.get_primary_image()
        self.assertTrue(image)
        self.assertEqual(image.mime_type, "image/jpeg")
        self.assertTrue(image.read())

    def test_get_image_invalid_data(self):
        tag = asf.ASF(self.f)
        tag["WM/Picture"] = [asf.ASFValue(b"nope", asf.BYTEARRAY)]
        tag.save()

        self.assertFalse(self.song.has_images)
        self.song.reload()
        self.assertTrue(self.song.has_images)

        image = self.song.get_primary_image()
        self.assertFalse(image)

    def test_unpack_image_min(self):
        data = b"\x03" + b"\x00" * 4 + b"\x00" * 4
        mime, desc, data, type_ = unpack_image(data)
        self.assertEqual(mime, u"")
        self.assertEqual(desc, u"")
        self.assertEqual(data, b"")
        self.assertEqual(type_, 3)

    def test_unpack_image_invalid(self):
        self.assertRaises(ValueError, unpack_image, b"")
        self.assertRaises(ValueError, unpack_image, b"\x00" * 6)
        self.assertRaises(ValueError, unpack_image, b"\x00" * 8)
        self.assertRaises(ValueError, unpack_image, b"\x00" * 100)

    def test_pack_image(self):
        d = pack_image(
            u"image/jpeg", u"Description", b"foo", APICType.COVER_FRONT)
        mime, desc, data, type_ = unpack_image(d)
        self.assertEqual(mime, u"image/jpeg")
        self.assertEqual(desc, u"Description")
        self.assertEqual(data, b"foo")
        self.assertEqual(type_, APICType.COVER_FRONT)

    def test_clear_images(self):
        # cover case
        image = self.song2.get_primary_image()
        self.assertTrue(image)
        self.song2.clear_images()
        self.assertFalse(self.song2.has_images)
        self.song2.reload()
        image = self.song2.get_primary_image()
        self.assertFalse(image)

        # no cover case
        self.song.clear_images()

    def test_set_image(self):
        fileobj = BytesIO(b"foo")
        image = EmbeddedImage(fileobj, "image/jpeg", 10, 10, 8)
        self.assertFalse(self.song.has_images)
        self.song.set_image(image)
        self.assertTrue(self.song.has_images)

        image = self.song.get_primary_image()
        self.assertEqual(image.mime_type, "image/jpeg")
        self.assertEqual(image.read(), b"foo")

    def test_can_change_images(self):
        self.assertTrue(self.song.can_change_images)

    def test_can_multiple_values(self):
        self.assertTrue("artist" in self.song.can_multiple_values())
        self.assertTrue(self.song.can_multiple_values("genre"))
