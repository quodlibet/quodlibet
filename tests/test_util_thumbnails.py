# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet.util.path import mtime
from tests import TestCase, NamedTemporaryFile, get_data_path

from gi.repository import GdkPixbuf
from senf import fsn2uri, fsnative

import os

try:
    import hashlib as hash
except ImportError:
    import md5 as hash

from quodlibet.util import thumbnails


class TThumb(TestCase):
    def setUp(self):
        self.wide = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 150, 10)
        self.high = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 10, 100)
        self.small = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 10, 20)
        self.filename = get_data_path("test.png")

    def tearDown(self):
        p1 = thumbnails.get_cache_info(self.filename, (10, 10))[0]
        p2 = thumbnails.get_cache_info(self.filename, (1000, 1000))[0]
        for path in [p1, p2]:
            try:
                os.remove(path)
            except OSError:
                pass

    def test_get_thumbnail_folder(self):
        path = thumbnails.get_thumbnail_folder()
        assert isinstance(str(path), fsnative)

    def test_thumb_from_file(self):
        with open(self.filename, "rb") as h:
            thumb = thumbnails.get_thumbnail_from_file(h, (50, 60))
            assert thumb

    def test_thumb_from_file_temp(self):
        fn = NamedTemporaryFile()
        with open(self.filename, "rb") as h:
            fn.write(h.read())
        fn.flush()
        fn.seek(0, 0)

        thumb = thumbnails.get_thumbnail_from_file(fn, (50, 60))
        assert thumb
        fn.close()

    def test_thumb_from_file_temp_partial(self):
        fn = NamedTemporaryFile()
        with open(self.filename, "rb") as h:
            fn.write(h.read(10))
        fn.flush()
        fn.seek(0, 0)

        thumb = thumbnails.get_thumbnail_from_file(fn, (50, 60))
        assert thumb is None
        fn.close()

    def test_get_cache_info(self):
        p, s = thumbnails.get_cache_info(self.filename, (20, 20))
        assert s == 128
        assert "normal" in {p.name for p in p.parents}

        p, s = thumbnails.get_cache_info(self.filename, (20, 300))
        assert s == 256
        assert "large" in {p.name for p in p.parents}

    def test_recreate_broken_cache_file(self):
        thumb = thumbnails.get_thumbnail(self.filename, (50, 60), ignore_temp=False)
        assert thumb
        path, size = thumbnails.get_cache_info(self.filename, (50, 60))
        open(path, "wb").close()
        thumb = thumbnails.get_thumbnail(self.filename, (50, 60), ignore_temp=False)
        assert thumb

    def test_thumb(self):
        thumb = thumbnails.get_thumbnail(self.filename, (50, 60), ignore_temp=False)

        # check for right scaling
        assert thumb
        assert thumb.get_width(), thumb.get_height() == (50, 25)

        # test the thumbnail filename
        uri = fsn2uri(self.filename)
        name = hash.md5(uri.encode("ascii")).hexdigest() + ".png"

        path = thumbnails.get_thumbnail_folder()
        path = os.path.join(path, "normal", name)

        assert os.path.isfile(path)

        # check for metadata
        thumb_pb = GdkPixbuf.Pixbuf.new_from_file(path)
        meta_mtime = thumb_pb.get_option("tEXt::Thumb::MTime")
        meta_uri = thumb_pb.get_option("tEXt::Thumb::URI")

        assert int(meta_mtime) == int(mtime(self.filename))
        assert meta_uri == uri

        # check rights
        if os.name != "nt":
            assert os.stat(path).st_mode == 33152
