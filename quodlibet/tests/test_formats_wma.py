# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import shutil
import StringIO

from mutagen import asf

from tests import TestCase, add, DATA_DIR, mkstemp
from quodlibet.formats.wma import WMAFile, unpack_image, pack_image
from quodlibet.formats._image import APICType, EmbeddedImage


class TWMAFile(TestCase):

    def setUp(self):
        self.f = mkstemp(".wma")[1]
        shutil.copy(os.path.join(DATA_DIR, 'test.wma'), self.f)
        self.song = WMAFile(self.f)

        self.f2 = mkstemp(".wma")[1]
        shutil.copy(os.path.join(DATA_DIR, 'test-2.wma'), self.f2)
        self.song2 = WMAFile(self.f2)

    def tearDown(self):
         os.unlink(self.f)
         os.unlink(self.f2)

    def test_basic(self):
        self.song["title"] = u"SomeTestValue"
        self.song.write()
        self.song.reload()
        self.assertEqual(self.song("title"), u"SomeTestValue")

    def test_length(self):
        self.assertEqual(self.song("~#length"), 3)

    def test_bitrate(self):
        self.assertEqual(self.song("~#bitrate"), 64)

    def test_write(self):
        self.song.write()

    def test_can_change(self):
        self.assertTrue(self.song.can_change("title"))
        self.assertFalse(self.song.can_change("foobar"))
        self.assertTrue("albumartist" in self.song.can_change())

    def test_invalid(self):
        path = os.path.join(DATA_DIR, 'empty.xm')
        self.assertTrue(os.path.exists(path))
        self.assertRaises(Exception, WMAFile, path)

    def test_get_image(self):
        self.assertFalse(self.song.get_primary_image())

        image = self.song2.get_primary_image()
        self.assertTrue(image)
        self.assertEqual(image.mime_type, "image/jpeg")
        self.assertTrue(image.file.read())

    def test_get_image_invalid_data(self):
        tag = asf.ASF(self.f)
        tag["WM/Picture"] = [asf.ASFValue("nope", asf.BYTEARRAY)]
        tag.save()

        self.assertFalse(self.song.has_images)
        self.song.reload()
        self.assertTrue(self.song.has_images)

        image = self.song.get_primary_image()
        self.assertFalse(image)

    def test_unpack_image_min(self):
        data = "\x03" + "\x00" *4 + "\x00" * 4
        mime, desc, data, type_ = unpack_image(data)
        self.assertEqual(mime, u"")
        self.assertEqual(desc, u"")
        self.assertEqual(data, "")
        self.assertEqual(type_, 3)

    def test_unpack_image_invalid(self):
        self.assertRaises(ValueError, unpack_image, "")
        self.assertRaises(ValueError, unpack_image, "\x00" * 6)
        self.assertRaises(ValueError, unpack_image, "\x00" * 8)
        self.assertRaises(ValueError, unpack_image, "\x00" * 100)

    def test_pack_image(self):
        d = pack_image(
            u"image/jpeg", u"Description", "foo", APICType.COVER_FRONT)
        mime, desc, data, type_ = unpack_image(d)
        self.assertEqual(mime, u"image/jpeg")
        self.assertEqual(desc, u"Description")
        self.assertEqual(data, "foo")
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
        fileobj = StringIO.StringIO("foo")
        image = EmbeddedImage("image/jpeg", 10, 10, 8, fileobj)
        self.assertFalse(self.song.has_images)
        self.song.set_image(image)
        self.assertTrue(self.song.has_images)

        image = self.song.get_primary_image()
        self.assertEqual(image.mime_type, "image/jpeg")
        self.assertEqual(image.file.read(), "foo")

    def test_can_change_images(self):
        self.assertTrue(self.song.can_change_images)

add(TWMAFile)
