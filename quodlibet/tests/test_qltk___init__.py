from tests import TestCase, add

import gtk

from quodlibet import qltk

class TQltk(TestCase):
    def test_none(self):
        self.failUnless(qltk.get_top_parent(None) is None)
    
    def test_gtp(self):
        w = gtk.Window(); l = gtk.Label()
        self.failUnlessEqual(qltk.get_top_parent(w), w)
        self.failUnlessEqual(qltk.get_top_parent(l), None)
        w.destroy(); l.destroy()

    def test_gtp_packed(self):
        w = gtk.Window(); l = gtk.Label(); w.add(l)
        self.failUnlessEqual(qltk.get_top_parent(w), w)
        self.failUnlessEqual(qltk.get_top_parent(l), w)
        w.destroy(); l.destroy()

    def test_is_accel(self):
        e = gtk.gdk.Event(gtk.gdk.KEY_RELEASE)
        self.failIf(qltk.is_accel(e, "a"))

        e = gtk.gdk.Event(gtk.gdk.KEY_PRESS)
        e.keyval = 65293
        e.state =  gtk.gdk.CONTROL_MASK
        self.failUnless(qltk.is_accel(e, "<ctrl>Return"))

    def test_popup_menu_under_widget(self):
        w = gtk.Window()
        l = gtk.Label()
        w.add(l)
        m = gtk.Menu()
        l.realize()
        qltk.popup_menu_under_widget(m, l, 1, 0)
        w.destroy()
        m.destroy()

add(TQltk)
