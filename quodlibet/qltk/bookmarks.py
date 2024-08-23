# Copyright 2006 Joe Wreschnig
#        2016-17 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# FIXME: Only allow one bookmark window per song.

from gi.repository import Gtk, Pango

from quodlibet import qltk, print_w
from quodlibet import util
from quodlibet import _

from quodlibet.qltk.views import RCMHintedTreeView
from quodlibet.util import connect_obj
from quodlibet.qltk import Icons


def MenuItems(marks, player, seekable):
    sizes = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
    items = []
    if not marks or marks[0][0] != 0:
        # Translators: Refers to the beginning of the playing song.
        marks.insert(0, (0, _("Beginning")))
    for time, mark in marks:
        i = Gtk.MenuItem()
        # older pygobject (~3.2) added a child on creation
        if i.get_child():
            i.remove(i.get_child())
        connect_obj(i, "activate", player.seek, time * 1000)
        i.set_sensitive(time >= 0 and seekable)
        hbox = Gtk.HBox(spacing=12)
        i.add(hbox)
        if time < 0:
            l = Gtk.Label(label=_("N/A"))
        else:
            l = Gtk.Label(label=util.format_time(time))
        l.set_alignment(0.0, 0.5)
        sizes.add_widget(l)
        hbox.pack_start(l, False, True, 0)
        text = Gtk.Label(mark)
        text.set_max_width_chars(80)
        text.set_ellipsize(Pango.EllipsizeMode.END)
        text.set_alignment(0.0, 0.5)
        hbox.pack_start(text, True, True, 0)
        i.show_all()
        items.append(i)
    return items


class EditBookmarksPane(Gtk.VBox):
    def __init__(self, library, song, close=False):
        super().__init__(spacing=6)

        hb = Gtk.HBox(spacing=12)
        self.time = time = Gtk.Entry()
        time.set_width_chars(5)
        self.markname = name = Gtk.Entry()
        add = qltk.Button(_("_Add"), Icons.LIST_ADD, Gtk.IconSize.MENU)
        hb.pack_start(time, False, True, 0)
        hb.pack_start(name, True, True, 0)
        hb.pack_start(add, False, True, 0)
        self.pack_start(hb, False, True, 0)

        model = Gtk.ListStore(int, str)
        sw = Gtk.ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.IN)
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.add(RCMHintedTreeView(model=model))

        render = Gtk.CellRendererText()

        def cdf(column, cell, model, iter, data):
            if model[iter][0] < 0:
                cell.set_property("text", _("N/A"))
            else:
                cell.set_property("text", util.format_time(model[iter][0]))
        render.set_property("editable", True)
        render.connect("edited", self.__edit_time, model)
        col = Gtk.TreeViewColumn(_("Time"), render)
        col.set_cell_data_func(render, cdf, None)
        sw.get_child().append_column(col)

        render = Gtk.CellRendererText()
        render.set_property("ellipsize", Pango.EllipsizeMode.END)
        col = Gtk.TreeViewColumn(_("Bookmark Name"), render, text=1)
        render.set_property("editable", True)
        render.connect("edited", self.__edit_name, model)
        sw.get_child().append_column(col)
        self.pack_start(sw, True, True, 0)
        self.accels = Gtk.AccelGroup()

        hbox = Gtk.HButtonBox()
        remove = qltk.Button(_("_Remove"), Icons.LIST_REMOVE)
        remove.set_sensitive(False)
        hbox.pack_start(remove, True, True, 0)
        if close:
            self.close = qltk.Button(_("_Close"), Icons.WINDOW_CLOSE)
            hbox.pack_start(self.close, True, True, 0)
        else:
            hbox.set_layout(Gtk.ButtonBoxStyle.END)
        self.pack_start(hbox, False, True, 0)

        connect_obj(add, "clicked", self.__add, model, time, name)

        model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        model.connect("row-changed", self._set_bookmarks, library, song)
        model.connect("row-inserted", self._set_bookmarks, library, song)

        selection = sw.get_child().get_selection()
        selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        selection.connect("changed", self.__check_selection, remove)
        remove.connect("clicked", self.__remove, selection, library, song)

        connect_obj(time, "changed", self.__check_entry, add, time, name)
        connect_obj(name, "changed", self.__check_entry, add, time, name)
        connect_obj(name, "activate", Gtk.Button.clicked, add)

        time.set_text(_("MM:SS"))
        connect_obj(time, "activate", Gtk.Entry.grab_focus, name)
        name.set_text(_("Bookmark Name"))

        menu = Gtk.Menu()
        remove = qltk.MenuItem(_("_Remove"), Icons.LIST_REMOVE)
        remove.connect("activate", self.__remove, selection, library, song)
        keyval, mod = Gtk.accelerator_parse("Delete")
        remove.add_accelerator(
            "activate", self.accels, keyval, mod, Gtk.AccelFlags.VISIBLE)
        menu.append(remove)
        menu.show_all()
        sw.get_child().connect("popup-menu", self.__popup, menu)
        sw.get_child().connect("key-press-event",
                                self.__view_key_press, remove)
        connect_obj(self, "destroy", Gtk.Menu.destroy, menu)

        self.__fill(model, song)

    def __view_key_press(self, view, event, remove):
        if event.keyval == Gtk.accelerator_parse("Delete")[0]:
            remove.activate()

    def __popup(self, view, menu):
        return view.popup_menu(menu, 0, Gtk.get_current_event_time())

    def __edit_name(self, render, path, new, model):
        if new:
            model[path][1] = new

    def __edit_time(self, render, path, new, model):
        try:
            time = util.parse_time(new, False)
        except Exception:
            pass
        else:
            model[path][0] = time

    def __check_entry(self, add, time, name):
        try:
            util.parse_time(time.get_text(), False)
        except Exception:
            add.set_sensitive(False)
        else:
            add.set_sensitive(bool(name.get_text()))

    def __add(self, model, time, name):
        try:
            time = util.parse_time(time.get_text(), False)
        except Exception:
            pass
        else:
            model.append([time, name.get_text()])

    def __check_selection(self, selection, remove):
        remove.set_sensitive(bool(selection.get_selected_rows()[1]))

    def __remove(self, remove, selection, library, song):
        model, paths = selection.get_selected_rows()
        if model:
            for path in paths:
                model.remove(model.get_iter(path))
            self._set_bookmarks(model, None, None, library, song)

    def _set_bookmarks(self, model, a, b, library, song):
        def stringify(s):
            return s.decode("utf-8") if isinstance(s, bytes) else s
        try:
            song.bookmarks = [(t, stringify(l)) for t, l in model]
        except (AttributeError, ValueError) as e:
            print_w(f"Couldn't save bookmark for {song('~filename')} ({e})")
        else:
            if library is not None:
                library.changed([song])

    def __fill(self, model, song):
        model.clear()
        for time, mark in song.bookmarks:
            model.append([time, mark])


class EditBookmarks(qltk.Window):
    def __init__(self, parent, library, player):
        super().__init__()
        self.set_transient_for(qltk.get_top_parent(parent))
        self.set_border_width(12)
        self.set_default_size(350, 250)
        self.set_title(_("Bookmarks") + " - %s" % player.song.comma("title"))

        pane = EditBookmarksPane(library, player.song, close=True)
        self.add(pane)

        s = library.connect("removed", self.__check_lock, player.song)
        connect_obj(self, "destroy", library.disconnect, s)

        position = player.get_position() // 1000
        pane.time.set_text(util.format_time(position))
        pane.markname.grab_focus()
        pane.close.connect("clicked", lambda *x: self.destroy())

        self.get_child().show_all()

    def __check_lock(self, library, songs, song):
        if song in songs:
            for c in self.get_child().get_children()[:-1]:
                c.set_sensitive(False)
