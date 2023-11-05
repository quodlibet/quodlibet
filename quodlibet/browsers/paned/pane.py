# Copyright 2013 Christoph Reiter
#           2023 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import operator

from gi.repository import Gtk, Pango, Gdk

from quodlibet import qltk
from quodlibet.qltk.views import AllTreeView, TreeViewColumnButton
from quodlibet.qltk.songsmenu import SongsMenu
from quodlibet.qltk.properties import SongProperties
from quodlibet.qltk.information import Information
from quodlibet.qltk import is_accel
from quodlibet.util import connect_obj

from .models import PaneModel
from .util import PaneConfig


class Pane(AllTreeView):
    """Pane of the paned browser"""

    TARGET_INFO_QL = 1
    TARGET_INFO_URI_LIST = 2

    def __init__(self, library, prefs, next_=None):
        super().__init__()
        self.set_fixed_height_mode(True)

        self.config = PaneConfig(prefs)
        self.__next = next_
        self.__restore_values = None

        self.__no_fill = 0

        column = TreeViewColumnButton(title=self.config.title)

        def on_column_header_clicked(column, event):
            # In case the column header gets clicked select the "All" entry
            if event.button != Gdk.BUTTON_PRIMARY or \
                    event.type != Gdk.EventType.BUTTON_PRESS:
                return Gdk.EVENT_PROPAGATE
            self.set_selected([])
            return Gdk.EVENT_STOP

        column.set_clickable(True)
        column.connect("button-press-event", on_column_header_clicked)
        column.set_use_markup(True)
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column.set_fixed_width(60)

        render = Gtk.CellRendererText()
        render.set_property("ellipsize", Pango.EllipsizeMode.END)
        column.pack_start(render, True)

        def text_cdf(column, cell, model, iter_, data):
            entry = model.get_value(iter_)
            is_markup, text = entry.get_text(self.config)
            if is_markup:
                cell.markup = text
                cell.set_property("markup", text)
            else:
                cell.markup = None
                cell.set_property("text", text)

        column.set_cell_data_func(render, text_cdf)

        render_count = Gtk.CellRendererText()
        render_count.set_property("xalign", 1.0)
        render_count.set_property("max-width-chars", 5)
        column.pack_end(render_count, True)
        # Tiny columns break too much rendering
        column.set_min_width(150)

        def count_cdf(column, cell, model, iter_, data):
            entry = model.get_value(iter_)
            markup = entry.get_count_text(self.config)
            cell.markup = markup
            cell.set_property("markup", markup)

        column.set_cell_data_func(render_count, count_cdf)
        self.append_column(column)

        model = PaneModel(self.config)
        self.set_model(model)

        self.set_search_equal_func(self.__search_func, None)
        self.set_search_column(0)
        self.set_enable_search(True)

        selection = self.get_selection()
        selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        self.__sig = self.connect(
            "selection-changed", self.__selection_changed)
        s = self.connect("popup-menu", self.__popup_menu, library)
        connect_obj(self, "destroy", self.disconnect, s)

        targets = [
            ("text/x-quodlibet-songs", Gtk.TargetFlags.SAME_APP,
             self.TARGET_INFO_QL),
            ("text/uri-list", 0, self.TARGET_INFO_URI_LIST)
        ]
        targets = [Gtk.TargetEntry.new(*t) for t in targets]

        self.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, targets,
                             Gdk.DragAction.COPY)
        self.connect("drag-data-get", self.__drag_data_get)
        self.connect("destroy", self.__destroy)

        librarian = library.librarian or library
        self.connect("key-press-event", self.__key_pressed, librarian)

    def __key_pressed(self, view, event, librarian):
        # if ctrl+a is pressed, intercept and select the All entry instead
        if is_accel(event, "<Primary>a"):
            self.set_selected([])
            return True
        elif is_accel(event, "<Primary>Return", "<Primary>KP_Enter"):
            qltk.enqueue(self.__get_selected_songs(sort=True))
            return True
        elif is_accel(event, "<alt>Return"):
            songs = self.__get_selected_songs(sort=True)
            if songs:
                window = SongProperties(librarian, songs, parent=self)
                window.show()
            return True
        elif is_accel(event, "<Primary>I"):
            songs = self.__get_selected_songs(sort=True)
            if songs:
                window = Information(librarian, songs, self)
                window.show()
            return True
        return False

    def __repr__(self):
        return "<%s config=%r>" % (type(self).__name__, self.config)

    def parse_restore_string(self, config_value):
        assert isinstance(config_value, str)

        values = config_value.split("\t")[:-1]

        try:
            if int(values[0]):
                values[0] = None
            else:
                del values[0]
        except (ValueError, IndexError):
            pass

        self.__restore_values = values

    def get_restore_string(self):
        values = self.get_selected()

        # The first value tells us if All was selected
        all_ = None in values
        if all_:
            values.remove(None)
        all_ = str(int(bool(all_)))
        values = list(values)
        values.insert(0, all_)

        # The config lib strips all whitespace,
        # so add a bogus . at the end
        values.append(u".")

        return u"\t".join(values)

    @property
    def tags(self):
        """Tags this pane displays"""

        return self.config.tags

    def __destroy(self, *args):
        # needed for gc
        self.__next = None

    def __search_func(self, model, column, key, iter_, data):
        entry = model.get_value(iter_)
        return not entry.contains_text(key)

    def __drag_data_get(self, view, ctx, sel, tid, etime):
        songs = self.__get_selected_songs(sort=True)

        if tid == self.TARGET_INFO_QL:
            qltk.selection_set_songs(sel, songs)
        else:
            sel.set_uris([song("~uri") for song in songs])

    def __popup_menu(self, view, library):
        songs = self.__get_selected_songs(sort=True)
        menu = SongsMenu(library, songs)
        menu.show_all()
        return view.popup_menu(menu, 0, Gtk.get_current_event_time())

    def __selection_changed(self, *args):
        if self.__next:
            self.__next.fill(self.__get_selected_songs())

    def add(self, songs):
        self.get_model().add_songs(songs)

    def remove(self, songs, remove_if_empty=True):
        self.inhibit()
        self.get_model().remove_songs(songs, remove_if_empty)
        self.uninhibit()

    def matches(self, song):
        model, paths = self.get_selection().get_selected_rows()

        # nothing == all
        if not paths:
            return True

        return model.matches(paths, song)

    def inhibit(self):
        """Inhibit selection change events and song propagation"""

        self.__no_fill += 1
        self.handler_block(self.__sig)

    def uninhibit(self):
        """Uninhibit selection change events and song propagation"""

        self.handler_unblock(self.__sig)
        self.__no_fill -= 1

    def fill(self, songs):
        # Restore the selection
        if self.__restore_values is not None:
            selected = self.__restore_values
            self.__restore_values = None
        else:
            selected = self.get_selected()

        model = self.get_model()
        # If previously all entries were selected or None: select All
        if not selected or len(model) == len(selected):
            selected = [None]

        self.inhibit()
        with self.without_model():
            model.clear()
            model.add_songs(songs)

        self.set_selected(selected, jump=True)
        self.uninhibit()

        if self.__next and self.__no_fill == 0:
            self.__next.fill(self.__get_selected_songs())

    def scroll(self, song):
        """Select and scroll to entry which contains song"""

        def select_func(row):
            entry = row[0]
            return entry.contains_song(song)

        self.select_by_func(select_func, one=True)

    def list(self, tag):
        return self.get_model().list(tag)

    def get_selected(self):
        """A list of keys for selected entries"""

        model, paths = self.get_selection().get_selected_rows()
        return model.get_keys(paths)

    def set_selected(self, values, jump=False, force_any=True):
        """Select entries with key in values

        jump -- scroll the the first selected entry
        any -- if nothing gets selected, select the first entry
        """

        if self.get_model().is_empty():
            return

        values = values or []

        # If the selection is the same, change nothing
        if values != self.get_selected():
            self.inhibit()
            self.get_selection().unselect_all()

            def select_func(row):
                entry = row[0]
                return entry.key in values

            self.select_by_func(select_func, scroll=jump)
            self.uninhibit()

            self.get_selection().emit("changed")

        if force_any and self.get_selection().count_selected_rows() == 0:
            self.set_cursor((0,))

    def set_selected_by_tag(self, tag, values, *args, **kwargs):
        """Select the entries which songs all have one of
        the values for the given tag.
        """

        pattern_values = self.get_model().get_keys_by_tag(tag, values)
        self.set_selected(pattern_values, *args, **kwargs)

    def __get_selected_songs(self, sort=False):
        model, paths = self.get_selection().get_selected_rows()
        songs = model.get_songs(paths)
        if sort:
            return sorted(songs, key=operator.attrgetter("sort_key"))
        return songs
