import tempfile
import os
import gtk

from tests import TestCase, add
from quodlibet import config
from quodlibet.formats._audio import AudioFile
from quodlibet.qltk.cover import CoverImage, BigCenteredImage, ResizeImage

class TCoverImage(TestCase):
    def setUp(self):
        config.init()
        self.fn = tempfile.mkstemp()[1]
        pb = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, 150, 10)
        pb.save(self.fn, "png")

    def tearDown(self):
        config.quit()
        os.remove(self.fn)

    def test_set_song(self):
        c = CoverImage()
        c.set_song(AudioFile({"~filename":"woo"}))
        event = gtk.gdk.Event(gtk.gdk.BUTTON_PRESS)
        event.button = 1
        c.emit("button-press-event", event)
        c.destroy()

    def test_big_window(self):
        w = BigCenteredImage("foobar", self.fn)
        w.destroy()

    def test_resize(self):
        w = ResizeImage(False)
        w.set_path(self.fn)
        w.set_path(None)
        w.destroy()

add(TCoverImage)
