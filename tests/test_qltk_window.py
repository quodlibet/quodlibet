# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase, skipIf

from quodlibet.qltk.window import Window, on_first_map, Dialog
from quodlibet.util import InstanceTracker, is_osx

from .helper import realized


class TWindow(TestCase):

    def test_on_first_map(self):
        w = Window()

        calls = []

        def foo(*args):
            calls.append(args)

        on_first_map(w, foo, 1)
        w.show()
        self.assertEqual(calls, [(1,)])
        on_first_map(w, foo, 2)
        self.assertEqual(calls, [(1,), (2,)])
        w.destroy()

    def test_ctr(self):
        Window().destroy()

    def test_instance_tracking(self):

        class SomeWindow(Window, InstanceTracker):
            def __init__(self):
                super().__init__()
                self._register_instance()

        self.assertFalse(SomeWindow.windows)
        other = Window()
        a = SomeWindow()
        self.assertTrue(a in SomeWindow.windows)
        self.assertTrue(a in SomeWindow.instances())
        a.destroy()
        self.assertFalse(SomeWindow.instances())
        self.assertTrue(SomeWindow.windows)
        other.destroy()
        self.assertFalse(SomeWindow.windows)

    def test_show_maybe(self):
        Window.prevent_inital_show(True)
        w = Window()
        w.show_maybe()
        self.assertFalse(w.get_visible())
        Window.prevent_inital_show(False)
        w.show_maybe()
        self.assertTrue(w.get_visible())
        w.destroy()

    def test_use_header_bar(self):
        w = Window(title="foo")
        w.use_header_bar()
        self.assertEqual(w.get_title(), "foo")
        w.destroy()

        w = Window()
        w.use_header_bar()
        self.assertEqual(w.get_title(), None)
        w.destroy()

    @skipIf(is_osx(), "crashes on 10.13")
    def test_toggle_fullscreen(self):
        w = Window(title="foo")
        w.toggle_fullscreen()
        with realized(w):
            w.toggle_fullscreen()
            w.toggle_fullscreen()
        w.destroy()


class TDialog(TestCase):

    def test_add_icon_button(self):
        d = Dialog()
        w = d.add_icon_button("foo", "bar", 100)
        self.assertEqual(d.get_widget_for_response(100), w)
