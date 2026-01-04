# Copyright 2006 Joe Wreschnig
#        2016-25 Nick Boultbee
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
from quodlibet.formats import AudioFile

from quodlibet.qltk.views import RCMHintedTreeView
from quodlibet.util import connect_obj
from quodlibet.qltk import Icons, add_css, get_children


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
        hbox = Gtk.Box(spacing=12)
        i.add(hbox)
        if time < 0:
            l = Gtk.Label(label=_("N/A"))
        else:
            l = Gtk.Label(label=util.format_time(time))
        l.set_xalign(0.0)
        l.set_yalign(0.5)
        sizes.add_widget(l)
        hbox.prepend(l)
        text = Gtk.Label(label=mark)
        text.set_max_width_chars(80)
        text.set_ellipsize(Pango.EllipsizeMode.END)
        text.set_xalign(0.0)
        text.set_yalign(0.5)
        hbox.prepend(text)
        i.show_all()
        items.append(i)
    return items


class EditBookmarksPane(Gtk.Box):
    song: AudioFile | None

    def __init__(
        self,
        parent,
        library,
        close: bool = False,
        song: AudioFile | None = None,
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.title = _("Bookmarks")

        self.model = model = Gtk.ListStore(int, str)
        if song:
            self._set_song(song)
        else:
            self.song = None

        self.hb = hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.time = time = Gtk.Entry()
        time.set_width_chars(5)
        time.set_size_request(65, -1)
        self.markname = name = Gtk.Entry()
        self.add = add = qltk.Button(_("_Add"), Icons.LIST_ADD, Gtk.IconSize.MENU)
        # GTK4: Use append() with hexpand instead of pack_start()
        hb.append(time)
        name.set_hexpand(True)
        hb.append(name)
        hb.append(add)
        self.append(hb)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_child(RCMHintedTreeView(model=model))
        add_css(sw, "* { padding: 12px } ")

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
        # GTK4: Use append() with vexpand for scrolled window
        sw.set_vexpand(True)
        self.append(sw)
        add_css(self, "* { margin: 12px } ")
        self.accels = Gtk.AccelGroup()

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.remove = remove = qltk.Button(_("_Remove"), Icons.LIST_REMOVE)
        remove.set_sensitive(False)
        hbox.prepend(remove)
        if close:
            self.close = qltk.Button(_("_Close"), Icons.WINDOW_CLOSE)
            hbox.prepend(self.close)
        else:
            hbox.set_layout(Gtk.ButtonBoxStyle.END)
        self.prepend(hbox)

        connect_obj(add, "clicked", self.__add, model, time, name)

        model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self._csig = model.connect("row-changed", self._set_bookmarks, library)
        self._isig = model.connect("row-inserted", self._set_bookmarks, library)

        selection = sw.get_child().get_selection()
        selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        selection.connect("changed", self.__check_selection, remove)
        remove.connect("clicked", self.__remove, selection, library)

        connect_obj(time, "changed", self.__check_entry, add, time, name)
        connect_obj(name, "changed", self.__check_entry, add, time, name)
        # GTK4: Gtk.Button.clicked() as method removed, use emit() instead
        name.connect("activate", lambda entry: add.emit("clicked"))

        time.set_placeholder_text(_("MM:SS"))
        connect_obj(time, "activate", Gtk.Entry.grab_focus, name)
        name.set_placeholder_text(_("Bookmark Name"))

        menu = Gtk.PopoverMenu()
        remove = qltk.MenuItem(_("_Remove"), Icons.LIST_REMOVE)
        remove.connect("activate", self.__remove, selection, library)
        keyval, mod = Gtk.accelerator_parse("Delete")
        remove.add_accelerator(
            "activate", self.accels, keyval, mod, Gtk.AccelFlags.VISIBLE
        )
        menu.append(remove)
        menu.show_all()
        sw.get_child().connect("popup-menu", self.__popup, menu)
        sw.get_child().connect("key-press-event", self.__view_key_press, remove)
        # GTK4: Gtk.Menu removed, use PopoverMenu
        self.connect("destroy", lambda _: menu.destroy())
        if parent:
            parent.connect("changed", self.__parent_changed)

    def __parent_changed(self, parent, songs):
        self.model.handler_block(self._csig)
        self.model.handler_block(self._isig)
        if len(songs) == 1:
            self._set_song(songs[0])
        else:
            self.model.clear()
            self.song = None
            self._set_enabled(False)
        self.model.handler_unblock(self._csig)
        self.model.handler_unblock(self._isig)

    def _set_song(self, song: AudioFile):
        self.song = song
        self.__fill(self.model, self.song)
        self._set_enabled(True)

    def _set_enabled(self, value: bool) -> None:
        self.set_sensitive(value)
        self.set_tooltip_text(_("Select a single track to edit its bookmarks"))

    def __view_key_press(self, view, event, remove):
        if event.keyval == Gtk.accelerator_parse("Delete")[0]:
            remove.activate()

    def __popup(self, view, menu):
        return view.popup_menu(menu, 0, GLib.CURRENT_TIME)

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

    def __remove(self, remove, selection, library):
        model, paths = selection.get_selected_rows()
        if model:
            for path in paths:
                model.remove(model.get_iter(path))
            self._set_bookmarks(model, None, None, library)

    def _set_bookmarks(self, model, a, b, library):
        if not self.song:
            return

        def stringify(s):
            return s.decode("utf-8") if isinstance(s, bytes) else s

        try:
            self.song.bookmarks = [(t, stringify(l)) for t, l in model]
        except (AttributeError, ValueError) as e:
            print_w(f"Couldn't save bookmark for {self.song('~filename')} ({e})")
        else:
            if library is not None:
                library.changed([self.song])

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
        self.set_title(_("Bookmarks") + " - {}".format(player.song.comma("title")))

        pane = EditBookmarksPane(None, library, song=player.song, close=True)
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
            for c in get_children(self.get_child())[:-1]:
                c.set_sensitive(False)
