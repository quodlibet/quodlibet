from tests import TestCase, add

import gtk
import os
import urllib
try:
    import hashlib as hash
except ImportError:
    import md5 as hash

from quodlibet.util import thumbnails
from quodlibet.util import mtime

class TThumb(TestCase):
    def setUp(s):
        s.wide = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, 150, 10)
        s.high = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, 10, 100)
        s.small = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, 10, 20)
        s.filename = os.path.join(os.getcwd(), "test_thumbnail.png")
        s.wide.save(s.filename, "png")

    def tearDown(s):
        os.remove(s.filename)

    def test_scale(s):
        nw = thumbnails.scale(s.wide, (50, 30))
        s.failUnlessEqual((nw.get_width(), nw.get_height()), (50, 3))

        nh = thumbnails.scale(s.high, (100, 20))
        s.failUnlessEqual((nh.get_width(), nh.get_height()), (2, 20))

        ns = thumbnails.scale(s.small, (500, 300))
        s.failUnlessEqual((ns.get_width(), ns.get_height()), (150, 300))

        ns = thumbnails.scale(s.small, (500, 300), scale_up=False)
        s.failUnlessEqual((ns.get_width(), ns.get_height()), (10, 20))

    def test_thumb(s):
        thumb = thumbnails.get_thumbnail(s.filename, (50, 60))

        #check for right scaling
        s.failUnless(thumb)
        s.failUnlessEqual((thumb.get_width(), thumb.get_height()), (50, 3))

        #test the thumbnail filename
        uri = "file://" + urllib.pathname2url(s.filename)
        name = hash.md5(uri).hexdigest() + ".png"
        path = os.path.expanduser("~/.thumbnails")
        # newer spec
        new_path = os.path.expanduser("~/.cache/thumbnails")
        if os.path.exists(new_path):
            path = new_path
        path = os.path.join(path, "normal", name)

        s.failUnless(os.path.isfile(path))

        #check for metadata
        thumb_pb = gtk.gdk.pixbuf_new_from_file(path)
        meta_mtime = thumb_pb.get_option("tEXt::Thumb::MTime")
        meta_uri = thumb_pb.get_option("tEXt::Thumb::URI")

        s.failUnlessEqual(int(meta_mtime), int(mtime(s.filename)))
        s.failUnlessEqual(meta_uri, uri)

        #check rights
        s.failUnlessEqual(os.stat(path).st_mode, 33152)

add(TThumb)
