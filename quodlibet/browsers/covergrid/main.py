# Copyright 2004-2007 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2009-2010 Steven Robertson
#           2012-2023 Nick Boultbee
#           2009-2014 Christoph Reiter
#           2022 Thomas Leberbauer
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


import os

from gi.repository import GLib, Gtk, Gdk, Gio

from .prefs import Preferences, DEFAULT_PATTERN_TEXT

import quodlibet
from quodlibet import app
from quodlibet import ngettext
from quodlibet import config
from quodlibet import qltk
from quodlibet import util
from quodlibet import _
from quodlibet.browsers import Browser
from quodlibet.browsers.albums.main import (
    AlbumTagCompletion,
    PreferencesButton as AlbumPreferencesButton,
)
from quodlibet.browsers.covergrid.models import (
    AlbumListFilterModel,
    AlbumListModel,
    AlbumListSortModel,
)
from quodlibet.browsers.covergrid.widgets import AlbumWidget
from quodlibet.browsers._base import DisplayPatternMixin
from quodlibet.query import Query
from quodlibet.qltk.information import Information
from quodlibet.qltk.properties import SongProperties
from quodlibet.qltk.songsmenu import SongsMenu
from quodlibet.qltk.x import MenuItem, Align, ScrolledWindow, RadioMenuItem
from quodlibet.qltk.x import SymbolicIconImage
from quodlibet.qltk.searchbar import SearchBarBox
from quodlibet.qltk.menubutton import MenuButton
from quodlibet.qltk import Icons
from quodlibet.util import connect_destroy
from quodlibet.util import connect_obj
from quodlibet.qltk import popup_menu_at_widget


class PreferencesButton(AlbumPreferencesButton):
    def __init__(self, browser, model):
        Gtk.Box.__init__(self)

        sort_orders = [
            (_("_Title"), self.__compare_title),
            (_("_People"), self.__compare_people),
            (_("_Date"), self.__compare_date),
            (_("_Date Added"), self.__compare_date_added),
            (_("_Original Date"), self.__compare_original_date),
            (_("_Genre"), self.__compare_genre),
            (_("_Rating"), self.__compare_rating),
            (_("Play_count"), self.__compare_avgplaycount),
        ]

        menu = Gtk.PopoverMenu()

        sort_item = Gtk.MenuItem(label=_("Sort _by…"), use_underline=True)
        sort_menu = Gtk.PopoverMenu()

        active = config.getint("browsers", "album_sort", 1)

        item = None
        for i, (label, func) in enumerate(sort_orders):
            item = RadioMenuItem(group=item, label=label, use_underline=True)
            model.set_sort_func(100 + i, func)
            if i == active:
                model.set_sort_column_id(100 + i, Gtk.SortType.ASCENDING)
                item.set_active(True)
            item.connect(
                "toggled", util.DeferredSignal(self.__sort_toggled_cb), model, i
            )
            sort_menu.append(item)

        sort_item.set_submenu(sort_menu)
        menu.append(sort_item)

        pref_item = MenuItem(_("_Preferences"), Icons.PREFERENCES_SYSTEM)
        menu.append(pref_item)
        connect_obj(pref_item, "activate", Preferences, browser)

        menu.show_all()

        button = MenuButton(
            SymbolicIconImage(Icons.OPEN_MENU, Gtk.IconSize.NORMAL), arrow=True
        )
        button.set_menu(menu)
        self.prepend(button)


class CoverGridContainer(ScrolledWindow):
    def __init__(self, view):
        super().__init__(
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
        )
        self._view = view
        view.set_hadjustment(self.props.hadjustment)
        view.set_vadjustment(self.props.vadjustment)
        self.set_child(view)
        self.set_vexpand(True)

    def scroll_up(self):
        va = self.props.vadjustment
        va.props.value = va.props.lower

    def do_focus(self, direction):
        is_tab = (
            direction == Gtk.DirectionType.TAB_FORWARD
            or direction == Gtk.DirectionType.TAB_BACKWARD
        )
        if not is_tab:
            self._view.child_focus(direction)
            return True

        if self.get_focus_child():
            # [Tab] moves focus beyond this container
            return False

        if not self._view.grab_focus():
            self._view.child_focus(direction)
        return True


def _get_cover_size():
    mag = config.getfloat("browsers", "covergrid_magnification", 3.0)
    size = config.getint("browsers", "cover_size")
    if size <= 0:
        size = 48
    return mag * size


class CoverGrid(Browser, util.InstanceTracker, DisplayPatternMixin):
    __model = None

    _PATTERN_FN = os.path.join(quodlibet.get_user_dir(), "album_pattern")
    _DEFAULT_PATTERN_TEXT = DEFAULT_PATTERN_TEXT

    name = _("Cover Grid")
    accelerated_name = _("_Cover Grid")
    keys = ["CoverGrid"]
    priority = 5

    def pack(self, songpane):
        container = self.songcontainer
        # GTK4: pack1() → set_start_child()

        container.set_start_child(self)

        container.set_resize_start_child(True)

        container.set_shrink_start_child(False)
        # GTK4: pack2() → set_end_child()

        container.set_end_child(songpane)

        container.set_resize_end_child(True)

        container.set_shrink_end_child(False)
        return container

    def unpack(self, container, songpane):
        container.remove(songpane)
        container.remove(self)

    @classmethod
    def init(cls, library):
        super().load_pattern()

    @classmethod
    def _init_model(cls, library):
        if cls.__model is None:
            cls.__model = AlbumListModel(library)
            cls.__library = library

    @classmethod
    def _destroy_model(cls):
        cls.__model = None

    @classmethod
    def toggle_text(cls):
        text_visible = config.getboolean("browsers", "album_text", True)
        for covergrid in cls.instances():
            for widget in covergrid._live_widgets:
                widget.props.text_visible = text_visible

    @classmethod
    def toggle_item_all(cls):
        show = config.getboolean("browsers", "covergrid_all", True)
        for covergrid in cls.instances():
            covergrid.__model_filter.props.include_item_all = show

    @classmethod
    def toggle_wide(cls):
        wide = config.getboolean("browsers", "covergrid_wide", False)
        for covergrid in cls.instances():
            covergrid.songcontainer.set_orientation(
                Gtk.Orientation.HORIZONTAL if wide else Gtk.Orientation.VERTICAL
            )

    @classmethod
    def update_mag(cls):
        cover_size = _get_cover_size()
        for covergrid in cls.instances():
            for widget in covergrid._live_widgets:
                widget.cover_size = cover_size
            covergrid.view.queue_resize()

    def __init__(self, library):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        self.songcontainer = qltk.paned.ConfigRVPaned("browsers", "covergrid_pos", 0.4)
        if config.getboolean("browsers", "covergrid_wide", False):
            self.songcontainer.set_orientation(Gtk.Orientation.HORIZONTAL)

        self._register_instance()
        self._init_model(library)

        self.__cover_cancel = Gio.Cancellable()

        model_sort = AlbumListSortModel(model=self.__model)
        self.__model_filter = model_filter = AlbumListFilterModel(
            include_item_all=config.getboolean("browsers", "covergrid_all", True),
            child_model=model_sort,
        )

        # Realised AlbumWidgets,
        # kept so the live grid can be updated without iterating the whole model
        # (it only realises the visible items).
        self._live_widgets: set[AlbumWidget] = set()

        self.__selection = Gtk.MultiSelection(model=model_filter)
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self.__factory_setup)
        factory.connect("bind", self.__factory_bind)
        factory.connect("unbind", self.__factory_unbind)
        factory.connect("teardown", self.__factory_teardown)

        self.view = view = Gtk.GridView(
            model=self.__selection,
            factory=factory,
            max_columns=24,
            single_click_activate=False,
            enable_rubberband=True,
            vexpand=True,
            valign=Gtk.Align.START,
        )

        self.scrollwin = sw = CoverGridContainer(view)

        self.__selection.connect(
            "selection-changed",
            util.DeferredSignal(
                lambda *a: self.__update_songs(select_default=False), owner=self
            ),
        )

        drag_source = Gtk.DragSource()
        drag_source.set_actions(Gdk.DragAction.COPY)
        drag_source.connect("prepare", self.__drag_prepare)
        view.add_controller(drag_source)
        view.connect("activate", self.__child_activated)

        self.accelerators = Gtk.AccelGroup()
        search = SearchBarBox(
            completion=AlbumTagCompletion(), accel_group=self.accelerators
        )
        search.connect("query-changed", lambda *a: self.__update_filter())
        connect_obj(search, "focus-out", lambda w: w.grab_focus(), view)
        self.__search = search

        prefs = PreferencesButton(self, model_sort)
        search.prepend(prefs)
        self.append(Align(search, left=6, top=0))
        self.append(sw)

        self.__update_filter()
        model_filter.connect(
            "notify::filter",
            util.DeferredSignal(lambda *a: self.__update_songs(), owner=self),
        )

        self.connect("key-press-event", self.__key_pressed, library.librarian)
        self.connect("destroy", self.__destroy)

        if app.cover_manager:
            connect_destroy(app.cover_manager, "cover-changed", self.__cover_changed)

    def __factory_setup(self, factory, list_item):
        widget = AlbumWidget(
            display_pattern=self.display_pattern,
            cover_size=_get_cover_size(),
            padding=config.getint("browsers", "item_padding", 6),
            text_visible=config.getboolean("browsers", "album_text", True),
            cancelable=self.__cover_cancel,
        )
        widget.connect("songs-menu", self.__popup)
        list_item.set_child(widget)
        self._live_widgets.add(widget)

    def __factory_bind(self, factory, list_item):
        widget = list_item.get_child()
        widget._list_item = list_item
        widget.bind(list_item.get_item())

    def __factory_unbind(self, factory, list_item):
        list_item.get_child().unbind()

    def __factory_teardown(self, factory, list_item):
        self._live_widgets.discard(list_item.get_child())

    def __selected_items(self):
        bitset = self.__selection.get_selection()
        return [
            self.__selection.get_item(bitset.get_nth(i))
            for i in range(bitset.get_size())
        ]

    def __update_songs(self, select_default=True):
        songs = self.__get_selected_songs(sort=False)
        if not select_default or songs:
            self.songs_selected(songs)
        elif len(self.__model_filter):
            self.__selection.select_item(0, True)
        else:
            self.songs_selected(songs)

    def __key_pressed(self, widget, event, librarian):
        if qltk.is_accel(event, "<Primary>I"):
            songs = self.__get_selected_songs()
            if songs:
                window = Information(librarian, songs, self)
                window.show()
            return True
        if qltk.is_accel(event, "<Primary>Return", "<Primary>KP_Enter"):
            qltk.enqueue(self.__get_selected_songs())
            return True
        if qltk.is_accel(event, "<alt>Return"):
            songs = self.__get_selected_songs()
            if songs:
                window = SongProperties(librarian, songs, self)
                window.show()
            return True
        return False

    def __destroy(self, browser):
        self.__cover_cancel.cancel()

        self.view.set_model(None)
        self.__model_filter = None

        if not CoverGrid.instances():
            CoverGrid._destroy_model()

    def __cover_changed(self, manager, songs):
        songs = set(songs)
        size = self.props.scale_factor * _get_cover_size()

        # Reload the cover on the affected model items (visible or not).
        # Bound widgets refresh via the item's "notify::cover";
        # off-screen items keep the fresh cover cached for when they scroll back in.
        for item in self.__model_filter:
            if not songs:
                break
            album = item.album
            if album is None:
                continue
            match = songs & album.songs
            if match:
                item.load_cover(size, self.__cover_cancel)
                songs -= match

    def __update_filter(self, scroll_up=True):
        if scroll_up:
            self.scrollwin.scroll_up()

        q = self.__search.get_query(star=["~people", "album"])
        self.__model_filter.props.filter = None if q.matches_all else q.search

    def __popup(self, widget):
        list_item = getattr(widget, "_list_item", None)
        if list_item is None:
            return
        pos = list_item.get_position()
        if not self.__selection.is_selected(pos):
            self.__selection.select_item(pos, True)

        albums = self.__get_selected_albums()
        songs = self.__get_songs_from_albums(albums)

        button_label = ngettext(
            "Reload album _cover", "Reload album _covers", len(albums)
        )
        button = MenuItem(button_label, Icons.VIEW_REFRESH)
        button.connect("activate", self.__refresh_cover)

        menu = SongsMenu(self.__library, songs, items=[[button]])
        menu.show_all()
        popup_menu_at_widget(menu, widget, Gdk.BUTTON_SECONDARY, GLib.CURRENT_TIME)

    def __refresh_cover(self, menuitem):
        size = self.props.scale_factor * _get_cover_size()
        for item in self.__selected_items():
            item.load_cover(size, self.__cover_cancel)

    def refresh_all(self):
        pattern = self.display_pattern
        for widget in self._live_widgets:
            widget.display_pattern = pattern
        for item in self.__model_filter:
            item.format_label(pattern)

    def __get_selected_albums(self):
        items = []
        for item in self.__selected_items():
            album = item.album
            if album is None:
                model = self.__model_filter
                return [it.album for it in model if it.album is not None]
            items.append(album)
        return items

    def __get_songs_from_albums(self, albums, sort=True):
        # Sort first by how the albums appear in the model itself,
        # then within the album using the default order.
        songs = []
        if sort:
            for album in albums:
                songs.extend(sorted(album.songs, key=lambda s: s.sort_key))
        else:
            for album in albums:
                songs.extend(album.songs)
        return songs

    def __get_selected_songs(self, sort=True):
        albums = self.__get_selected_albums()
        return self.__get_songs_from_albums(albums, sort)

    def __drag_prepare(self, source, x, y):
        songs = self.__get_selected_songs()
        if not songs:
            return None
        files = [Gio.File.new_for_path(s("~filename")) for s in songs]
        return Gdk.ContentProvider.new_for_value(Gdk.FileList.new_from_list(files))

    def __child_activated(self, view, position):
        self.songs_activated()

    def active_filter(self, song):
        for album in self.__get_selected_albums():
            if song in album.songs:
                return True
        return False

    def can_filter_text(self):
        return True

    def filter_text(self, text):
        self.__search.set_text(text)
        if Query(text).is_parsable:
            self.__update_filter()
            self.__update_songs()

    def get_filter_text(self):
        return self.__search.get_text()

    def can_filter_albums(self):
        return True

    def can_filter(self, key):
        # Numerics are different for collections, and although title works,
        # it's not of much use here.
        if key is not None and (key.startswith("~#") or key == "title"):
            return False
        return super().can_filter(key)

    def filter_albums(self, values):
        changed = self.__select_by_func(
            lambda album: album is not None and album.key in values
        )
        self.view.grab_focus()
        if changed:
            self.__update_songs()

    def list_albums(self):
        model = self.__model_filter
        return [item.album.key for item in model if item.album is not None]

    def unfilter(self):
        self.filter_text("")

    def __select_by_func(self, func, scroll=True, one=False):
        first = True
        for i, item in enumerate(self.__model_filter):
            if not func(item.album):
                continue
            if first:
                self.__selection.select_item(i, True)
                if scroll:
                    self.view.scroll_to(i, Gtk.ListScrollFlags.NONE, None)
                first = False
                if one:
                    break
            else:
                self.__selection.select_item(i, False)
        return not first

    def save(self):
        conf = self.__get_config_string()
        config.settext("browsers", "covergrid", conf)
        text = self.__search.get_text()
        config.settext("browsers", "query_text", text)

    def restore(self):
        text = config.gettext("browsers", "query_text")
        entry = self.__search
        entry.set_text(text)

        if Query(text).is_parsable:
            self.__update_filter(scroll_up=False)

        keys = config.gettext("browsers", "covergrid", "").split("\n")

        if keys != [""]:
            self.__select_by_func(
                lambda album: album is not None and album.str_key in keys
            )
        else:
            self.__select_by_func(lambda album: album is None, one=True)

    def finalize(self, restored):
        if not restored:
            self.__select_by_func(lambda album: album is None, one=True)

    def scroll(self, song):
        album_key = song.album_key
        self.__select_by_func(
            lambda album: album is not None and album.key == album_key, one=True
        )

    def activate(self):
        self.__update_songs()

    def __get_config_string(self):
        albums = []
        for item in self.__selected_items():
            album = item.album
            if album is None:
                albums.clear()
                break
            albums.append(album)

        if not albums:
            return ""

        confval = "\n".join(a.str_key for a in albums)
        # ConfigParser strips a trailing \n so we move it to the front
        if confval and confval[-1] == "\n":
            confval = "\n" + confval[:-1]
        return confval
