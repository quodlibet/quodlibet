from tests import TestCase, add

from gi.repository import Gtk, Gdk
from gi.overrides import keysyms

from quodlibet import qltk


class TQltk(TestCase):
    def test_none(self):
        self.failUnless(qltk.get_top_parent(None) is None)

    def test_gtp(self):
        w = Gtk.Window()
        l = Gtk.Label()
        self.failUnlessEqual(qltk.get_top_parent(w), w)
        self.failUnlessEqual(qltk.get_top_parent(l), None)
        w.destroy()
        l.destroy()

    def test_gtp_packed(self):
        w = Gtk.Window()
        l = Gtk.Label()
        w.add(l)
        self.failUnlessEqual(qltk.get_top_parent(w), w)
        self.failUnlessEqual(qltk.get_top_parent(l), w)
        w.destroy()
        l.destroy()

    def test_is_accel(self):
        e = Gdk.Event.new(Gdk.EventType.KEY_RELEASE)
        self.failIf(qltk.is_accel(e, "a"))

        e = Gdk.Event.new(Gdk.EventType.KEY_PRESS)
        e.keyval = keysyms.Return
        e.state = Gdk.ModifierType.CONTROL_MASK
        self.failUnless(qltk.is_accel(e, "<ctrl>Return"))

    def test_popup_menu_under_widget(self):
        w = Gtk.Window()
        l = Gtk.Label()
        w.add(l)
        m = Gtk.Menu()
        l.realize()
        qltk.popup_menu_under_widget(m, l, 1, 0)
        w.destroy()
        m.destroy()

add(TQltk)
