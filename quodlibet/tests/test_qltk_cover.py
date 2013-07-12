import tempfile
import os

from gi.repository import Gtk, GdkPixbuf, Gdk

from tests import TestCase, add
from quodlibet import config
from quodlibet.formats._audio import AudioFile
from quodlibet.qltk.cover import CoverImage, BigCenteredImage, ResizeImage

class TCoverImage(TestCase):
    def setUp(self):
        config.init()
        self.fn = tempfile.mkstemp()[1]
        pb = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 150, 10)
        pb.savev(self.fn, "png", [], [])

    def tearDown(self):
        config.quit()
        os.remove(self.fn)

    def test_set_song(self):
        c = CoverImage()
        c.set_song(AudioFile({"~filename":"woo"}))
        event = Gdk.Event.new(Gdk.EventType.BUTTON_PRESS)
        event.type.button = 1
        c.emit("button-press-event", event)
        c.destroy()

    def test_big_window(self):
        parent = Gtk.Window()
        w = BigCenteredImage("foobar", self.fn, parent)
        w.destroy()

    def test_resize(self):
        w = ResizeImage(False)
        w.set_path(self.fn)
        w.set_path(None)
        w.destroy()

add(TCoverImage)
