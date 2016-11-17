# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from quodlibet.qltk import x
from quodlibet.qltk import Icons

from . import TestCase


class Notebook(TestCase):
    def test_widget_str(self):
        n = x.Notebook()
        c = Gtk.VBox()
        n.append_page(c, "A Test")
        self.failUnlessEqual("A Test", n.get_tab_label(c).get_text())
        n.destroy()

    def test_widget_label(self):
        l = Gtk.Label(label="A Test")
        n = x.Notebook()
        c = Gtk.VBox()
        n.append_page(c, l)
        self.failUnless(l is n.get_tab_label(c))
        c.destroy()

    def test_widget_error(self):
        n = x.Notebook()
        w = Gtk.VBox()
        self.failUnlessRaises(TypeError, n.append_page, w)
        w.destroy()
        n.destroy()


class Frame(TestCase):
    def test_label(self):
        self.failUnlessEqual(
            x.Frame("foo").get_label_widget().get_text(), "foo")


class MenuItem(TestCase):
    def test_ctr(self):
        self.failUnless(x.MenuItem("foo", Icons.EDIT_FIND))


class Button(TestCase):
    def test_ctr(self):
        self.failUnless(x.Button("foo", Icons.EDIT_FIND))


class TAlign(TestCase):
    def test_ctr(self):
        button = Gtk.Button()
        a = x.Align(button, left=2, right=4, top=5, bottom=-2, border=2)
        self.assertEqual(a.get_margin_top(), 7)
        self.assertEqual(a.get_margin_bottom(), 0)
        self.assertEqual(a.get_margin_left(), 4)
        self.assertEqual(a.get_margin_right(), 6)
        self.failUnless(a.get_child() is button)
        a.destroy()


class TScrolledWindow(TestCase):
    def test_ctr(self):
        w = x.ScrolledWindow()
        w.destroy()
