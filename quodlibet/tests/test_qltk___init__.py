# -*- coding: utf-8 -*-
from tests import TestCase

from gi.repository import Gtk, Gdk

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
        RETURN = 65293

        e = Gdk.Event.new(Gdk.EventType.KEY_RELEASE)
        self.failIf(qltk.is_accel(e, "a"))

        e = Gdk.Event.new(Gdk.EventType.KEY_PRESS)
        e.keyval = RETURN
        e.state = Gdk.ModifierType.CONTROL_MASK
        self.failUnless(qltk.is_accel(e, "<ctrl>Return"))

        e = Gdk.Event.new(Gdk.EventType.KEY_PRESS)
        e.keyval = RETURN
        e.state = Gdk.ModifierType.CONTROL_MASK
        self.failUnless(qltk.is_accel(e, "a", "<ctrl>Return"))
        self.failUnless(qltk.is_accel(e, "<ctrl>Return", "b"))
        self.failIf(qltk.is_accel(e, "a", "b"))

    def test_popup_menu_under_widget(self):
        w = Gtk.Window()
        l = Gtk.Label()
        w.add(l)
        m = Gtk.Menu()
        l.realize()
        qltk.popup_menu_under_widget(m, l, 1, 0)
        w.destroy()
        m.destroy()

    def test_redraw_all(self):
        qltk.redraw_all_toplevels()

    def test_get_menu_item_top_parent(self):
        item = Gtk.MenuItem()
        menu = Gtk.Menu()
        menu.append(item)
        window = Gtk.Window()
        menu.attach_to_widget(window, None)
        self.assertEqual(qltk.get_menu_item_top_parent(item), window)
