# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

from gi.repository import Gtk, Gdk
from quodlibet.fsn import fsn2bytes

from quodlibet.formats import AudioFile
from quodlibet import qltk
from quodlibet.qltk.pluginwin import PluginWindow
from quodlibet import util
from quodlibet.plugins import PluginManager
from tests.gtk_helpers import MockSelData


def test_is_instance_of_gtype_name():
    assert qltk.is_instance_of_gtype_name(Gtk.Button(), "GtkButton")
    assert qltk.is_instance_of_gtype_name(Gtk.Button(), "GtkWidget")
    assert not qltk.is_instance_of_gtype_name(Gtk.Button(), "GtkLabel")
    assert not qltk.is_instance_of_gtype_name(Gtk.Button(), "NopeNopeNope")


class TQltk(TestCase):
    def test_none(self):
        assert qltk.get_top_parent(None) is None

    def test_get_fg_highlight_color(self):
        widget = Gtk.Button()
        color = qltk.get_fg_highlight_color(widget.get_style_context())
        assert color is not None
        assert isinstance(color, Gdk.RGBA)

    def test_gtp(self):
        w = Gtk.Window()
        l = Gtk.Label()
        self.assertEqual(qltk.get_top_parent(w), w)
        self.assertEqual(qltk.get_top_parent(l), None)
        w.destroy()

    def test_gtp_packed(self):
        w = Gtk.Window()
        l = Gtk.Label()
        w.add(l)
        self.assertEqual(qltk.get_top_parent(w), w)
        self.assertEqual(qltk.get_top_parent(l), w)
        w.destroy()

    def test_is_accel_pressed(self):
        keyval = Gdk.KEY_Return
        state = Gdk.ModifierType.CONTROL_MASK
        assert qltk.is_accel_pressed(keyval, state, "<ctrl>Return")
        assert qltk.is_accel_pressed(keyval, state, "a", "<ctrl>Return")
        assert qltk.is_accel_pressed(keyval, state, "<ctrl>Return", "b")
        assert not qltk.is_accel_pressed(keyval, state, "a", "b")

    def test_is_accel_pressed_invalid(self):
        with self.assertRaises(ValueError):
            qltk.is_accel_pressed(Gdk.KEY_Return, Gdk.ModifierType(0), "NOPE")

    def test_is_accel_pressed_primary(self):
        if not util.is_osx():
            assert qltk.is_accel_pressed(
                Gdk.KEY_Return, Gdk.ModifierType.CONTROL_MASK, "<Primary>Return"
            )

    def test_popup_menu_under_widget(self):
        w = Gtk.Window()
        l = Gtk.Label()
        w.add(l)
        m = Gtk.PopoverMenu()
        m.attach_to_widget(l, None)
        qltk.popup_menu_under_widget(m, l, 1, 0)
        w.destroy()

    def test_redraw_all(self):
        qltk.redraw_all_toplevels()

    def test_get_menu_item_top_parent(self):
        window = Gtk.Window()
        box = Gtk.Box()
        window.set_child(box)
        label = Gtk.Label()
        box.append(label)
        self.assertEqual(qltk.get_menu_item_top_parent(label), window)

    def test_get_menu_item_top_parent_sub(self):
        window = Gtk.Window()
        box = Gtk.Box()
        window.set_child(box)
        inner = Gtk.Box()
        box.append(inner)
        label = Gtk.Label()
        inner.append(label)
        self.assertEqual(qltk.get_menu_item_top_parent(label), window)

    def test_get_menu_item_top_parent_unattached(self):
        label = Gtk.Label()
        assert qltk.get_menu_item_top_parent(label) is None

    def test_show_uri_with_existing_window(self):
        PluginManager.instance = PluginManager()
        # Force an instance
        win = PluginWindow()
        qltk.show_uri("foo", "quodlibet:///prefs/plugins/Squeezebox Output")
        # TODO: proper assertions, etc
        win.destroy()

    def test_get_font_backend_name(self):
        name = qltk.get_font_backend_name()
        assert isinstance(name, str)


class Tselection_data(TestCase):
    def test_selection_set_songs(self):
        song = AudioFile()
        song["~filename"] = "foo"
        sel = MockSelData()
        qltk.selection_set_songs(sel, [song])
        assert sel.data == fsn2bytes("foo", "utf-8")

        assert qltk.selection_get_filenames(sel) == ["foo"]
