# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from quodlibet.qltk import x
from quodlibet.qltk import Icons
from quodlibet.qltk import add_css

from . import TestCase
from .helper import visible


class Notebook(TestCase):
    def test_widget_str(self):
        n = x.Notebook()
        c = Gtk.VBox()
        n.append_page(c, "A Test")
        self.assertEqual(n.get_tab_label(c).get_text(), "A Test")
        n.destroy()

    def test_widget_label(self):
        l = Gtk.Label(label="A Test")
        n = x.Notebook()
        c = Gtk.VBox()
        n.append_page(c, l)
        assert l is n.get_tab_label(c)
        c.destroy()

    def test_widget_error(self):
        n = x.Notebook()
        w = Gtk.VBox()
        self.assertRaises(TypeError, n.append_page, w)
        w.destroy()
        n.destroy()

    def test_edge_flush_stays_within_parent(self):
        # Preferences packs the notebook flush against the window when a
        # header-bar close button is present and hides the notebook border.
        # Forcing a 1px border in do_size_allocate expands past the parent.
        window = Gtk.Window(type=Gtk.WindowType.POPUP)
        container = Gtk.VBox()
        notebook = x.Notebook()
        notebook.set_show_border(False)
        add_css(
            notebook,
            """
            * {
                border-width: 0px;
            }
            """,
        )
        page = Gtk.Label(label="Page")
        notebook.append_page(page, "Page")
        container.pack_start(notebook, True, True, 0)
        window.add(container)

        def assert_within_container():
            origin = notebook.translate_coordinates(container, 0, 0)
            self.assertIsNotNone(origin)
            dx, dy = origin
            self.assertGreaterEqual(dx, 0)
            self.assertGreaterEqual(dy, 0)
            n_alloc = notebook.get_allocation()
            c_alloc = container.get_allocation()
            self.assertLessEqual(dx + n_alloc.width, c_alloc.width)
            self.assertLessEqual(dy + n_alloc.height, c_alloc.height)

        try:
            with visible(window, width=400, height=300):
                assert_within_container()
                window.resize(520, 380)
                while Gtk.events_pending():
                    Gtk.main_iteration()
                assert_within_container()
        finally:
            window.destroy()


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
