# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, Gdk, GObject

from tests import TestCase, skipIf
from quodlibet.qltk.getstring import GetStringDialog
from quodlibet.qltk import is_wayland


class _ClipboadTestClass(GetStringDialog):
    _OK = True

    def _verify_clipboard(self, text):
        if self._OK:
            return text
        return None


@skipIf(is_wayland(), "blocks under wayland for some reason")
class TGetStringDialog(TestCase):
    def setUp(self):
        parent = Gtk.Window()
        self.gsd1 = GetStringDialog(parent, "title", "enter a string")
        self.gsd2 = _ClipboadTestClass(parent, "title", "enter a string")

    def test_getstring(self):
        ret = self.gsd1.run(text="foobar", test=True)
        self.assertEqual(ret, "foobar")

    def test_tooltip(self):
        foo = GetStringDialog(Gtk.Window(), "title", "", tooltip="foo bar")
        self.assertEqual(foo._val.get_tooltip_text(), "foo bar")

    def test_clipboard(self):
        display = Gdk.Display.get_default()
        if display is None:
            return
        clipboard = display.get_clipboard()
        value = GObject.Value(str, "42")
        clipboard.set_content(Gdk.ContentProvider.new_for_value(value))
        ret = self.gsd2.run(text="24", clipboard=True, test=True)
        self.assertEqual(ret, "42")
        clipboard.set_content(None)

    def tearDown(self):
        self.gsd1.destroy()
        self.gsd2.destroy()
