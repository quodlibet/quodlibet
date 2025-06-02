# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

from gi.repository import Gtk, Gdk
from senf import fsnative, fsn2bytes

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
        l.destroy()

    def test_gtp_packed(self):
        w = Gtk.Window()
        l = Gtk.Label()
        w.add(l)
        self.assertEqual(qltk.get_top_parent(w), w)
        self.assertEqual(qltk.get_top_parent(l), w)
        w.destroy()
        l.destroy()

    def test_is_accel(self):
        e = Gdk.Event.new(Gdk.EventType.KEY_RELEASE)
        assert not qltk.is_accel(e, "a")

        e = Gdk.Event.new(Gdk.EventType.KEY_PRESS)
        e.keyval = Gdk.KEY_Return
        e.state = Gdk.ModifierType.CONTROL_MASK
        assert qltk.is_accel(e, "<ctrl>Return")

        e = Gdk.Event.new(Gdk.EventType.KEY_PRESS)
        e.keyval = Gdk.KEY_Return
        e.state = Gdk.ModifierType.CONTROL_MASK
        assert qltk.is_accel(e, "a", "<ctrl>Return")
        assert qltk.is_accel(e, "<ctrl>Return", "b")
        assert not qltk.is_accel(e, "a", "b")

    def test_is_accel_invalid(self):
        e = Gdk.Event.new(Gdk.EventType.KEY_PRESS)
        with self.assertRaises(ValueError):
            qltk.is_accel(e, "NOPE")

    def test_is_accel_primary(self):
        e = Gdk.Event.new(Gdk.EventType.KEY_PRESS)
        e.keyval = Gdk.KEY_Return
        e.state = Gdk.ModifierType.CONTROL_MASK
        if not util.is_osx():
            assert qltk.is_accel(e, "<Primary>Return")

    def test_popup_menu_under_widget(self):
        w = Gtk.Window()
        l = Gtk.Label()
        w.add(l)
        m = Gtk.PopoverMenu()
        m.attach_to_widget(l, None)
        w.show_all()
        qltk.popup_menu_under_widget(m, l, 1, 0)
        w.destroy()
        m.destroy()

    def test_redraw_all(self):
        qltk.redraw_all_toplevels()

    def test_get_menu_item_top_parent(self):
        item = Gtk.MenuItem()
        menu = Gtk.PopoverMenu()
        menu.append(item)
        window = Gtk.Window()
        menu.attach_to_widget(window, None)
        self.assertEqual(qltk.get_menu_item_top_parent(item), window)

    def test_get_menu_item_top_parent_sub(self):
        item = Gtk.MenuItem()
        menu = Gtk.PopoverMenu()
        menu.append(item)
        window = Gtk.Window()
        menu.attach_to_widget(window, None)
        sub = Gtk.PopoverMenu()
        sub_item = Gtk.MenuItem()
        sub.append(sub_item)
        item.set_submenu(sub)
        self.assertEqual(qltk.get_menu_item_top_parent(sub_item), window)

    def test_get_menu_item_top_parent_unattached(self):
        item = Gtk.MenuItem()
        menu = Gtk.PopoverMenu()
        menu.append(item)
        assert qltk.get_menu_item_top_parent(item) is None

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
        song["~filename"] = fsnative("foo")
        sel = MockSelData()
        qltk.selection_set_songs(sel, [song])
        assert sel.data == fsn2bytes(fsnative("foo"), "utf-8")

        assert qltk.selection_get_filenames(sel) == [fsnative("foo")]
