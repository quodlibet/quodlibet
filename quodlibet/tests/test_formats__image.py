# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from tests import TestCase, add, DATA_DIR, mkstemp

import os

from quodlibet.formats._audio import AudioFile
from quodlibet.formats._image import EmbeddedImage, APICType


class TAPICType(TestCase):

    def test_basic(self):
        self.assertEqual(APICType.COVER_FRONT, 3)

    def test_sort_key(self):
        values = [
            APICType.OTHER, APICType.COVER_FRONT, APICType.FILE_ICON,
            APICType.ARTIST, APICType.PUBLISHER_LOGOTYPE
        ]

        values.sort(key=APICType.sort_key)

        wanted = [
            APICType.OTHER, APICType.FILE_ICON, APICType.PUBLISHER_LOGOTYPE,
            APICType.ARTIST, APICType.COVER_FRONT
        ]

        self.assertEqual(values, wanted)

add(TAPICType)


class TImageContainer(TestCase):

    def setUp(self):
        self.a = AudioFile()

    def test_default_get(self):
        self.assertFalse(self.a.get_primary_image())

    def test_has_image(self):
        self.assertFalse(self.a.has_images)
        self.a["~picture"] = "y"
        self.assertTrue(self.a.has_images)
        self.a.has_images = False
        self.assertFalse(self.a.has_images)

    def test_default_can_change(self):
        self.assertFalse(self.a.can_change_images)
add(TImageContainer)


class TEmbeddedImages(TestCase):

    def setUp(self):
        from gi.repository import GdkPixbuf

        self.filename = mkstemp()[1]
        pb = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 150, 10)
        pb.savev(self.filename, "png", [], [])

    def tearDown(self):
        os.remove(self.filename)

    def test_repr(self):
        image = EmbeddedImage.from_path(self.filename)
        repr(image)

    def test_from_path(self):
        image = EmbeddedImage.from_path(self.filename)
        self.assertTrue(image)
        self.assertEqual(image.file.name, self.filename)
        self.assertEqual(image.mime_type, "image/png")
        self.assertEqual(image.width, 150)
        self.assertEqual(image.height, 10)
        self.assertEqual(image.color_depth, 8)

    def test_from_path_bogus(self):
        image = EmbeddedImage.from_path(self.filename + "nope")
        self.assertFalse(image)

    def test_not_an_image(self):
        path = os.path.join(DATA_DIR, 'test-2.wma')
        image = EmbeddedImage.from_path(path)
        self.assertFalse(image)

    def test_get_extensions(self):
        image = EmbeddedImage.from_path(self.filename)
        self.assertTrue("png" in image.extensions)

    def test_from_path_empty(self):
        empty = mkstemp()[1]
        try:
            image = EmbeddedImage.from_path(empty)
            self.assertFalse(image)
        finally:
            os.remove(empty)
add(TEmbeddedImages)
