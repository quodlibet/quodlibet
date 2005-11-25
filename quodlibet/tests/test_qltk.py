from tests import TestCase, add
import gtk, qltk

class get_top_parent(TestCase):
    def test_none(self):
        self.failUnless(qltk.get_top_parent(None) is None)
    
    def test_gtp(self):
        w = gtk.HBox(); l = gtk.Label()
        self.failUnlessEqual(qltk.get_top_parent(w), w)
        self.failUnlessEqual(qltk.get_top_parent(l), l)
        w.destroy(); l.destroy()

    def test_gtp_packed(self):
        w = gtk.HBox(); l = gtk.Label(); w.pack_start(l)
        self.failUnlessEqual(qltk.get_top_parent(w), w)
        self.failUnlessEqual(qltk.get_top_parent(l), w)
        w.destroy(); l.destroy()
add(get_top_parent)

