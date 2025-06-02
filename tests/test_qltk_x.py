# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from quodlibet.qltk import x
from quodlibet.qltk import Icons

from . import TestCase
from .helper import visible


class Notebook(TestCase):
    def test_widget_str(self):
        n = x.Notebook()
        c = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, )
        n.append_page(c, "A Test")
        self.assertEqual(n.get_tab_label(c).get_text(), "A Test")
        n.destroy()

    def test_widget_label(self):
        l = Gtk.Label(label="A Test")
        n = x.Notebook()
        c = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, )
        n.append_page(c, l)
        assert l is n.get_tab_label(c)
        c.destroy()

    def test_widget_error(self):
        n = x.Notebook()
        w = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, )
        self.assertRaises(TypeError, n.append_page, w)
        w.destroy()
        n.destroy()


class Frame(TestCase):
    def test_label(self):
        self.assertEqual(x.Frame("foo").get_label_widget().get_text(), "foo")


class MenuItem(TestCase):
    def test_ctr(self):
        assert x.MenuItem("foo", Icons.EDIT_FIND)


class Button(TestCase):
    def test_ctr(self):
        assert x.Button("foo", Icons.EDIT_FIND)


class TAlign(TestCase):
    def test_ctr(self):
        button = Gtk.Button()
        a = x.Align(button, left=2, right=4, top=5, bottom=-2, border=2)
        self.assertEqual(a.get_margin_top(), 7)
        self.assertEqual(a.get_margin_bottom(), 0)
        self.assertEqual(a.get_margin_left(), 4)
        self.assertEqual(a.get_margin_right(), 6)
        assert a.get_child() is button
        a.destroy()


class TScrolledWindow(TestCase):
    def test_ctr(self):
        w = x.ScrolledWindow()
        w.destroy()


class THighlightToggleButton(TestCase):
    def test_main(self):
        w = x.HighlightToggleButton()
        w.set_active(True)
        with visible(w):
            pass
        w.set_active(False)
        with visible(w):
            pass
        w.destroy()
