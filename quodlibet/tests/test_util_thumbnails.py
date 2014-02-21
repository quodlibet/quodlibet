from quodlibet.util.path import mtime
from tests import TestCase, NamedTemporaryFile

from gi.repository import Gtk, GdkPixbuf

import os
import urllib
try:
    import hashlib as hash
except ImportError:
    import md5 as hash

from quodlibet.util import thumbnails
from quodlibet.util.path import expanduser, pathname2url, is_fsnative


class TThumb(TestCase):
    def setUp(s):
        s.wide = GdkPixbuf.Pixbuf.new(
            GdkPixbuf.Colorspace.RGB, True, 8, 150, 10)
        s.high = GdkPixbuf.Pixbuf.new(
            GdkPixbuf.Colorspace.RGB, True, 8, 10, 100)
        s.small = GdkPixbuf.Pixbuf.new(
            GdkPixbuf.Colorspace.RGB, True, 8, 10, 20)
        s.filename = os.path.join(os.getcwd(), "test_thumbnail.png")
        s.wide.savev(s.filename, "png", [], [])

    def tearDown(s):
        os.remove(s.filename)

    def test_calc_scale_size(self):
        self.assertRaises(ValueError,
                          thumbnails.calc_scale_size, (1, 1), (1, 0))
        res = thumbnails.calc_scale_size((100, 100), (500, 100))
        self.assertEqual(res, (100, 20))

    def test_add_border(self):
        res = thumbnails.add_border(self.small, 10)
        self.assertEqual(res.get_width(), 10 + 2)
        self.assertEqual(res.get_height(), 20 + 2)

    def test_get_thumbnail_folder(self):
        path = thumbnails.get_thumbnail_folder()
        self.assertTrue(is_fsnative(path))

    def test_scale(s):
        nw = thumbnails.scale(s.wide, (50, 30))
        s.failUnlessEqual((nw.get_width(), nw.get_height()), (50, 3))

        nh = thumbnails.scale(s.high, (100, 20))
        s.failUnlessEqual((nh.get_width(), nh.get_height()), (2, 20))

        ns = thumbnails.scale(s.small, (500, 300))
        s.failUnlessEqual((ns.get_width(), ns.get_height()), (150, 300))

        ns = thumbnails.scale(s.small, (500, 300), scale_up=False)
        s.failUnlessEqual((ns.get_width(), ns.get_height()), (10, 20))

    def test_thumb_from_file(self):
        with open(self.filename, "rb") as h:
            thumb = thumbnails.get_thumbnail_from_file(h, (50, 60))
            self.assertTrue(thumb)

    def test_thumb_from_file_temp(self):
        fn = NamedTemporaryFile()
        with open(self.filename, "rb") as h:
            fn.write(h.read())
        fn.flush()
        fn.seek(0, 0)

        thumb = thumbnails.get_thumbnail_from_file(fn, (50, 60))
        self.assertTrue(thumb)
        fn.close()

    def test_thumb_from_file_temp_partial(self):
        fn = NamedTemporaryFile()
        with open(self.filename, "rb") as h:
            fn.write(h.read(10))
        fn.flush()
        fn.seek(0, 0)

        thumb = thumbnails.get_thumbnail_from_file(fn, (50, 60))
        self.assertTrue(thumb is None)
        fn.close()

    def test_thumb(s):
        thumb = thumbnails.get_thumbnail(s.filename, (50, 60))

        #check for right scaling
        s.failUnless(thumb)
        s.failUnlessEqual((thumb.get_width(), thumb.get_height()), (50, 3))

        #test the thumbnail filename
        uri = "file://" + pathname2url(s.filename)
        name = hash.md5(uri).hexdigest() + ".png"

        path = thumbnails.get_thumbnail_folder()
        path = os.path.join(path, "normal", name)

        s.failUnless(os.path.isfile(path))

        #check for metadata
        thumb_pb = GdkPixbuf.Pixbuf.new_from_file(path)
        meta_mtime = thumb_pb.get_option("tEXt::Thumb::MTime")
        meta_uri = thumb_pb.get_option("tEXt::Thumb::URI")

        s.failUnlessEqual(int(meta_mtime), int(mtime(s.filename)))
        s.failUnlessEqual(meta_uri, uri)

        #check rights
        if os.name != "nt":
            s.failUnlessEqual(os.stat(path).st_mode, 33152)
