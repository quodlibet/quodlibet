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

        s.failUnless(thumb)
        s.failUnlessEqual((thumb.get_width(), thumb.get_height()), (50, 3))

        uri = "file://" + urllib.pathname2url(s.filename)
        uri = hash.md5(uri).hexdigest() + ".png"

        path = os.path.expanduser("~/.thumbnails")
        path = os.path.join(path, "normal", uri)

        s.failUnless(os.path.isfile(path))
        s.failUnlessAlmostEqual(mtime(s.filename), mtime(path), places=3)
        s.failUnlessEqual(os.stat(path).st_mode, 33152)

add(TThumb)
