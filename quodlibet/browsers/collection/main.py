# Copyright 2010, 2012-2014 Christoph Reiter
#                      2017 Uriel Zajaczkovski
#                 2017-2023 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, GLib, Pango, Gdk

from quodlibet import qltk
from quodlibet import util
from quodlibet import config
from quodlibet import _
from quodlibet.browsers.albums import AlbumTagCompletion
from quodlibet.browsers import Browser
from quodlibet.query import Query

from quodlibet.qltk.information import Information
from quodlibet.qltk.properties import SongProperties
from quodlibet.qltk.searchbar import SearchBarBox
from quodlibet.qltk.songsmenu import SongsMenu
from quodlibet.qltk.views import AllTreeView
from quodlibet.qltk import Icons
from quodlibet.qltk.image import add_border_widget, get_surface_for_pixbuf
from quodlibet.qltk.x import ScrolledWindow, Align, SymbolicIconImage
from quodlibet.util import connect_obj, cmp
from quodlibet.util.library import background_filter

from .models import (
    CollectionTreeStore,
    CollectionSortModel,
    CollectionFilterModel,
    AlbumNode,
    _ORDERING,
)
from .prefs import get_headers, Preferences


class CollectionView(AllTreeView):
    def __init__(self):
        super().__init__()
        self.connect_after("row-expanded", self.__expand_helper)

    def __expand_helper(self, view, iter, path):
        model = view.get_model()
        children = list(model[path].iterchildren())
        if len(children) == 1:
            view.expand_row(children[0].path, False)

    def select_album(self, album, unselect=True):
        model = self.get_model()
        path = model.get_path_for_album(album)
        if path is not None:
            self.select_path(path, unselect)

    def select_path(self, path, unselect=True):
        path_idx = path
        if isinstance(path_idx, Gtk.TreePath):
            path_idx = path_idx.get_indices()
        for i, _x in enumerate(path_idx[:-1]):
            self.expand_row(Gtk.TreePath(tuple(path_idx[: i + 1])), False)
        self.scroll_to_cell(path, use_align=True, row_align=0.5)
        selection = self.get_selection()
        assert selection
        if unselect:
            selection.unselect_all()
            self.set_cursor(path)
        else:
            selection.select_path(path)

    def get_selected_albums(self):
        selection = self.get_selection()
        assert selection
        model, paths = selection.get_selected_rows()
        albums = set()
        for path in paths:
            albums.update(model.get_albums_for_path(path))
        return albums


class CollectionBrowser(Browser, util.InstanceTracker):
    name = _("Album Collection")
    accelerated_name = _("Album _Collection")
    keys = ["AlbumCollection", "CollectionBrowser"]
    priority = 6

    __model = None

    def pack(self, songpane):
        container = qltk.ConfigRHPaned("browsers", "collectionbrowser_pos", 0.4)
        container.pack1(self, True, False)
        container.pack2(songpane, True, False)
        return container

    def unpack(self, container, songpane):
        container.remove(songpane)
        container.remove(self)

    @classmethod
    def _init_model(cls, library):
        cls.__model = model = CollectionTreeStore()
        cls.__albums = albums = library.albums

        albums.load()
        cls.__sigs = [
            albums.connect("added", cls._add_albums, model),
            albums.connect("removed", cls._remove_albums, model),
            albums.connect("changed", cls._change_albums, model),
        ]

        cls.set_hierarchy()

    @classmethod
    def _destroy_model(cls):
        for sig in cls.__sigs:
            cls.__albums.disconnect(sig)
        cls.__model = None
        del cls.__sigs

    def _refilter(self):
        if hasattr(self, "view"):
            self.view.get_model().refilter()

    @classmethod
    def set_hierarchy(cls):
        cls.__model.set_albums(get_headers(), cls.__albums.values())
        for inst in cls.instances():
            inst._refilter()

    @classmethod
    def _add_albums(cls, library, added, model):
        model.add_albums(added)

    @classmethod
    def _remove_albums(cls, library, removed, model):
        model.remove_albums(removed)

    @classmethod
    def _change_albums(cls, library, changed, model):
        model.change_albums(changed)

    def __init__(self, library):
        super().__init__(spacing=6)
        self.set_orientation(Gtk.Orientation.VERTICAL)

        self._register_instance()
        if self.__model is None:
            self._init_model(library)

        sw = ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.IN)
        self.view = view = CollectionView()
        view.set_headers_visible(False)
        model_sort = CollectionSortModel(model=self.__model)
        model_filter = CollectionFilterModel(child_model=model_sort)
        self.__filter = None
        self.__bg_filter = background_filter()
        model_filter.set_visible_func(self.__parse_query)
        view.set_model(model_filter)

        def cmpa(a, b):
            """Like cmp but treats values that evaluate to false as inf"""
            if not a and b:
                return 1
            if not b and a:
                return -1
            return cmp(a, b)

        def cmp_rows(model, i1, i2, data):
            t1, t2 = model[i1][0], model[i2][0]
            pos1 = _ORDERING.get(t1, 0)
            pos2 = _ORDERING.get(t2, 0)
            if pos1 or pos2:
                return cmp(pos1, pos2)

            if not isinstance(t1, AlbumNode):
                return cmp(util.human_sort_key(t1), util.human_sort_key(t2))

            a1, a2 = t1.album, t2.album
            return (
                cmpa(a1.peoplesort, a2.peoplesort)
                or cmpa(a1.date, a2.date)
                or cmpa(a1.sort, a2.sort)
                or cmp(a1.key, a2.key)
            )

        model_sort.set_sort_func(0, cmp_rows)
        model_sort.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        column = Gtk.TreeViewColumn("albums")

        def cell_data(column, cell, model, iter_, data):
            markup = model.get_markup(self.__model.tags, iter_)
            cell.markup = markup
            cell.set_property("markup", markup)

        def get_scaled_cover(item):
            if item.scanned:
                return item.cover

            scale_factor = self.get_scale_factor()
            item.scan_cover(scale_factor=scale_factor)
            return item.cover

        def cell_data_pb(column, cell, model, iter_, data):
            album = model.get_album(iter_)
            if album is None:
                cell.set_property("icon-name", Icons.FOLDER)
            else:
                item = model.get_value(iter_)
                cover = get_scaled_cover(item)
                if cover:
                    cover = add_border_widget(cover, view)
                    surface = get_surface_for_pixbuf(self, cover)
                    cell.set_property("surface", surface)
                else:
                    cell.set_property("icon-name", Icons.MEDIA_OPTICAL)

        imgrender = Gtk.CellRendererPixbuf()
        render = Gtk.CellRendererText()
        if view.supports_hints():
            render.set_property("ellipsize", Pango.EllipsizeMode.END)
        column.pack_start(imgrender, False)
        column.pack_start(render, True)
        column.set_cell_data_func(render, cell_data)
        column.set_cell_data_func(imgrender, cell_data_pb)
        view.append_column(column)

        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.add(view)

        hbox = Gtk.HBox(spacing=6)

        prefs = Gtk.Button()
        prefs.add(SymbolicIconImage(Icons.PREFERENCES_SYSTEM, Gtk.IconSize.MENU))
        prefs.connect("clicked", lambda *x: Preferences(self))

        self.accelerators = Gtk.AccelGroup()
        search = SearchBarBox(
            completion=AlbumTagCompletion(), accel_group=self.accelerators
        )
        search.connect("query-changed", self.__update_filter)
        connect_obj(search, "focus-out", lambda w: w.grab_focus(), view)
        self.__search = search

        hbox.pack_start(search, True, True, 0)
        hbox.pack_start(prefs, False, True, 0)

        self.pack_start(Align(hbox, left=6, top=0), False, True, 0)
        self.pack_start(sw, True, True, 0)

        view.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        self.__sig = view.get_selection().connect("changed", self.__selection_changed)
        view.connect("row-activated", self.__play)
        connect_obj(view, "popup-menu", self.__popup, view, library)

        targets = [
            ("text/x-quodlibet-songs", Gtk.TargetFlags.SAME_APP, 1),
            ("text/uri-list", 0, 2),
        ]
        targets = [Gtk.TargetEntry.new(*t) for t in targets]

        view.drag_source_set(
            Gdk.ModifierType.BUTTON1_MASK, targets, Gdk.DragAction.COPY
        )
        view.connect("drag-data-get", self.__drag_data_get)

        self.connect("destroy", self.__destroy)
        self.connect("key-press-event", self.__key_pressed, library.librarian)

        self.show_all()

    def __inhibit(self):
        self.view.get_selection().handler_block(self.__sig)

    def __uninhibit(self):
        self.view.get_selection().handler_unblock(self.__sig)

    def __parse_query(self, model, iter_, data):
        f, b = self.__filter, self.__bg_filter
        if f is None and b is None:
            return True

        def check_album(obj):
            if b is None:
                return f(obj)
            if f is None:
                return b(obj)
            return f(obj) and b(obj)

        obj = model.get_value(iter_)
        if isinstance(obj, AlbumNode):
            return check_album(obj.album)
        for album in model.iter_albums(iter_):
            if check_album(album):
                return True
        return False

    def __update_filter(self, entry, text):
        self.__filter = None
        star = self.__model.tags + ["album"]
        query = self.__search.get_query(star)
        if not query.matches_all:
            self.__filter = query.search
        self.__bg_filter = background_filter()

        self.view.get_model().refilter()

    def __destroy(self, browser):
        klass = type(browser)
        if not klass.instances():
            klass._destroy_model()

    def __drag_data_get(self, view, ctx, sel, tid, etime):
        songs = self.__get_selected_songs()
        if tid == 1:
            qltk.selection_set_songs(sel, songs)
        else:
            sel.set_uris([song("~uri") for song in songs])

    def __popup(self, view, library):
        songs = self.__get_selected_songs(view.get_selection())
        menu = SongsMenu(library, songs)
        menu.show_all()
        return view.popup_menu(menu, 0, Gtk.get_current_event_time())

    def __play(self, view, path, col):
        model = view.get_model()
        if isinstance(model[path][0], AlbumNode):
            self.songs_activated()
        else:
            if view.row_expanded(path):
                view.collapse_row(path)
            else:
                view.expand_row(path, False)

    def __get_selected_songs(self, sort=True):
        albums = self.view.get_selected_albums()
        songs = []
        if sort:
            for album in albums:
                songs.extend(sorted(album.songs))
        else:
            for album in albums:
                songs.extend(album.songs)
        return songs

    def __selection_changed(self, selection):
        songs = self.__get_selected_songs(False)
        if songs is not None:
            GLib.idle_add(self.songs_selected, songs)

    def __key_pressed(self, widget, event, librarian):
        if qltk.is_accel(event, "<Primary>I"):
            songs = self.__get_selected_songs()
            if songs:
                window = Information(librarian, songs, self)
                window.show()
            return True
        if qltk.is_accel(event, "<Primary>Return", "<Primary>KP_Enter"):
            qltk.enqueue(self.__get_selected_songs(sort=True))
            return True
        if qltk.is_accel(event, "<alt>Return"):
            songs = self.__get_selected_songs()
            if songs:
                window = SongProperties(librarian, songs, self)
                window.show()
            return True
        return False

    def can_filter_albums(self):
        return True

    def filter_albums(self, album_keys):
        albums = [
            a for a in [self.__albums.get(k) for k in album_keys] if a is not None
        ]
        if albums:
            self.view.select_album(albums[0], unselect=True)
            self.view.grab_focus()
        for album in albums[1:]:
            self.view.select_album(album, unselect=False)

    def can_filter_text(self):
        return True

    def filter_text(self, text):
        self.__search.set_text(text)
        if Query(text).is_parsable:
            self.__update_filter(self.__search, text)
            self.activate()

    def get_filter_text(self):
        return self.__search.get_text()

    def unfilter(self):
        self.filter_text("")

    def activate(self):
        self.view.get_selection().emit("changed")

    def restore(self):
        paths = config.get("browsers", "collection", "").split("\t")
        paths = [tuple(map(int, path.split())) for path in paths]
        self.__inhibit()
        if paths:
            if not paths[0]:
                self.__uninhibit()
                return
            self.view.select_path(paths[0], unselect=True)
        for path in paths[1:]:
            self.view.select_path(path, unselect=False)
        self.__uninhibit()

    def scroll(self, song):
        album = self.__albums.get(song.album_key)
        if album:
            self.view.select_album(album)

    def save(self):
        model, paths = self.view.get_selection().get_selected_rows()
        paths = "\t".join([" ".join(map(str, path)) for path in paths])
        config.set("browsers", "collection", paths)


browsers = [CollectionBrowser]
