from tests import TestCase, add

import gtk

from qltk.sliderbutton import VSlider

class TVSlider(TestCase):
    Kind = VSlider
    def setUp(self):
        self.button = self.Kind()
        self.button.scale.set_range(0, 1)
        self.button.scale.set_value(0)

    def test_initial(self):
        v = self.button.scale.get_value()
        self.failUnlessAlmostEqual(v, 0)

    def test_scroll(self):
        ev = gtk.gdk.Event(gtk.gdk.SCROLL)
        ev.direction = gtk.gdk.SCROLL_UP
        self.button.emit('scroll-event', ev)
        self.failUnless(self.button.scale.get_value() > 0.0)

    def tearDown(self): self.button.destroy()
add(TVSlider)
