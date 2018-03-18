# -*- coding: utf-8 -*-
# Copyright 2004-2007 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2009-2010 Steven Robertson
#           2012-2018 Nick Boultbee
#           2009-2014 Christoph Reiter
#           2018      Uriel Zajaczkovski
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from __future__ import absolute_import

import os

from gi.repository import Gtk, Pango, Gdk, Gio

from .prefs import Preferences, DEFAULT_PATTERN_TEXT
from quodlibet.browsers.albums.models import (AlbumModel,
    AlbumFilterModel, AlbumSortModel, AlbumItem)
from quodlibet.browsers.albums.main import (AlbumTagCompletion,
    PreferencesButton, VisibleUpdate)

import quodlibet
from quodlibet import app
from quodlibet import ngettext
from quodlibet import config
from quodlibet import qltk
from quodlibet import util
from quodlibet import _
from quodlibet.browsers import Browser
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
from quodlibet.util.library import background_filter
from quodlibet.util import connect_obj
from quodlibet.qltk.cover import get_no_cover_pixbuf
from quodlibet.qltk.image import add_border_widget, get_surface_for_pixbuf
from quodlibet.qltk import popup_menu_at_widget


def get_cover_size_grid():
    return AlbumItem(None).COVER_SIZE_GRID


class PreferencesButton(PreferencesButton):
    def __init__(self, browser, model):
        Gtk.HBox.__init__(self)

        sort_orders = [
            (_("_Title"), self.__compare_title),
            (_("_Artist"), self.__compare_artist),
            (_("_Date"), self.__compare_date),
            (_("_Genre"), self.__compare_genre),
            (_("_Rating"), self.__compare_rating),
        ]

        menu = Gtk.Menu()

        sort_item = Gtk.MenuItem(
            label=_(u"Sort _by…"), use_underline=True)
        sort_menu = Gtk.Menu()

        active = config.getint('browsers', 'album_sort', 1)

        item = None
        for i, (label, func) in enumerate(sort_orders):
            item = RadioMenuItem(group=item, label=label,
                                 use_underline=True)
            model.set_sort_func(100 + i, func)
            if i == active:
                model.set_sort_column_id(100 + i, Gtk.SortType.ASCENDING)
                item.set_active(True)
            item.connect("toggled",
                         util.DeferredSignal(self.__sort_toggled_cb),
                         model, i)
            sort_menu.append(item)

        sort_item.set_submenu(sort_menu)
        menu.append(sort_item)

        pref_item = MenuItem(_("_Preferences"), Icons.PREFERENCES_SYSTEM)
        menu.append(pref_item)
        connect_obj(pref_item, "activate", Preferences, browser)

        menu.show_all()

        button = MenuButton(
                SymbolicIconImage(Icons.EMBLEM_SYSTEM, Gtk.IconSize.MENU),
                arrow=True)
        button.set_menu(menu)
        self.pack_start(button, True, True, 0)


class IconView(Gtk.IconView):
    # XXX: disable height for width etc. Speeds things up and doesn't seem
    # to break anyhting in a scrolled window

    def do_get_preferred_width_for_height(self, height):
        return (1, 1)

    def do_get_preferred_width(self):
        return (1, 1)

    def do_get_preferred_height(self):
        return (1, 1)

    def do_get_preferred_height_for_width(self, width):
        return (1, 1)


class CoverGrid(Browser, util.InstanceTracker, VisibleUpdate,
                DisplayPatternMixin):
    __gsignals__ = Browser.__gsignals__
    __model = None
    __last_render = None
    __last_render_surface = None

    _PATTERN_FN = os.path.join(quodlibet.get_user_dir(), "album_pattern")
    _DEFAULT_PATTERN_TEXT = DEFAULT_PATTERN_TEXT
    STAR = ["~people", "album"]

    name = _("Cover Grid")
    accelerated_name = _("_Cover Grid")
    keys = ["CoverGrid"]
    priority = 4

    def pack(self, songpane):
        container = self.songcontainer
        container.pack1(self, True, False)
        container.pack2(songpane, True, False)
        return container

    def unpack(self, container, songpane):
        container.remove(songpane)
        container.remove(self)

    @classmethod
    def init(klass, library):
        super(CoverGrid, klass).load_pattern()

    @classmethod
    def _destroy_model(klass):
        klass.__model.destroy()
        klass.__model = None

    @classmethod
    def toggle_text(klass):
        on = config.getboolean("browsers", "album_text", True)
        for covergrid in klass.instances():
            covergrid.__text_cells.set_visible(on)
            covergrid.view.queue_resize()

    @classmethod
    def toggle_wide(klass):
        wide = config.getboolean("browsers", "covergrid_wide", False)
        for covergrid in klass.instances():
            covergrid.songcontainer.set_orientation(
                Gtk.Orientation.HORIZONTAL if wide
                else Gtk.Orientation.VERTICAL)

    @classmethod
    def update_mag(klass):
        mag = config.getfloat("browsers", "covergrid_magnification", 3.)
        for covergrid in klass.instances():
            covergrid.__cover.set_property('width',
                get_cover_size_grid() * mag + 8)
            covergrid.__cover.set_property('height',
                get_cover_size_grid() * mag + 8)
            covergrid.view.set_item_width(get_cover_size_grid() * mag + 8)
            covergrid.view.queue_resize()
            covergrid.redraw()

    def redraw(self):
        model = self.__model
        for iter_, item in model.iterrows():
            album = item.album
            if album is not None:
                item.scanned = False
                model.row_changed(model.get_path(iter_), iter_)

    @classmethod
    def _init_model(klass, library):
        klass.__model = AlbumModel(library)
        klass.__library = library

    @classmethod
    def _refresh_albums(klass, albums):
        """We signal all other open album views that we changed something
        (Only needed for the cover atm) so they redraw as well."""
        if klass.__library:
            klass.__library.albums.refresh(albums)

    @util.cached_property
    def _no_cover(self):
        """Returns a cairo surface representing a missing cover"""

        mag = config.getfloat("browsers", "covergrid_magnification", 3.)

        cover_size = get_cover_size_grid()
        scale_factor = self.get_scale_factor() * mag
        pb = get_no_cover_pixbuf(cover_size, cover_size, scale_factor)
        return get_surface_for_pixbuf(self, pb)

    def __init__(self, library):
        Browser.__init__(self, spacing=6)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.songcontainer = qltk.paned.ConfigRVPaned(
            "browsers", "covergrid_pos", 0.4)
        if config.getboolean("browsers", "covergrid_wide", False):
            self.songcontainer.set_orientation(Gtk.Orientation.HORIZONTAL)

        self._register_instance()
        if self.__model is None:
            self._init_model(library)

        self._cover_cancel = Gio.Cancellable()

        self.scrollwin = sw = ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.IN)
        model_sort = AlbumSortModel(model=self.__model)
        model_filter = AlbumFilterModel(child_model=model_sort)
        self.view = view = IconView(model_filter)
        #view.set_item_width(get_cover_size_grid() + 12)
        self.view.set_row_spacing(config.getint("browsers", "row_spacing", 6))
        self.view.set_column_spacing(config.getint("browsers",
            "column_spacing", 6))
        self.view.set_item_padding(config.getint("browsers",
            "item_padding", 6))
        self.view.set_has_tooltip(True)
        self.view.connect("query-tooltip", self._show_tooltip)

        self.__bg_filter = background_filter()
        self.__filter = None
        model_filter.set_visible_func(self.__parse_query)

        mag = config.getfloat("browsers", "covergrid_magnification", 3.)

        self.view.set_item_width(get_cover_size_grid() * mag + 8)

        self.__cover = render = Gtk.CellRendererPixbuf()
        render.set_property('width', get_cover_size_grid() * mag + 8)
        render.set_property('height', get_cover_size_grid() * mag + 8)
        view.pack_start(render, False)

        def cell_data_pb(view, cell, model, iter_, no_cover):
            item = model.get_value(iter_)

            if item.album is None:
                surface = None
            elif item.cover:
                pixbuf = item.cover
                pixbuf = add_border_widget(pixbuf, self.view)
                surface = get_surface_for_pixbuf(self, pixbuf)
                # don't cache, too much state has an effect on the result
                self.__last_render_surface = None
            else:
                surface = no_cover

            if self.__last_render_surface == surface:
                return
            self.__last_render_surface = surface
            cell.set_property("surface", surface)

        view.set_cell_data_func(render, cell_data_pb, self._no_cover)

        self.__text_cells = render = Gtk.CellRendererText()
        render.set_visible(config.getboolean("browsers", "album_text", True))
        render.set_property('alignment', Pango.Alignment.CENTER)
        render.set_property('xalign', 0.5)
        render.set_property('ellipsize', Pango.EllipsizeMode.END)
        view.pack_start(render, False)

        def cell_data(view, cell, model, iter_, data):
            album = model.get_album(iter_)

            if album is None:
                text = "<b>%s</b>" % _("All Albums")
                text += "\n" + ngettext("%d album", "%d albums",
                        len(model) - 1) % (len(model) - 1)
                markup = text
            else:
                markup = self.display_pattern % album

            if self.__last_render == markup:
                return
            self.__last_render = markup
            cell.markup = markup
            cell.set_property('markup', markup)

        view.set_cell_data_func(render, cell_data, None)

        view.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.add(view)

        view.connect('item-activated', self.__play_selection, None)

        self.__sig = connect_destroy(
            view, 'selection-changed',
            util.DeferredSignal(self.__update_songs, owner=self))

        targets = [("text/x-quodlibet-songs", Gtk.TargetFlags.SAME_APP, 1),
                   ("text/uri-list", 0, 2)]
        targets = [Gtk.TargetEntry.new(*t) for t in targets]

        view.drag_source_set(
            Gdk.ModifierType.BUTTON1_MASK, targets, Gdk.DragAction.COPY)
        view.connect("drag-data-get", self.__drag_data_get) # NOT WORKING
        connect_obj(view, 'button-press-event',
            self.__rightclick, view, library)
        connect_obj(view, 'popup-menu', self.__popup, view, library)

        self.accelerators = Gtk.AccelGroup()
        search = SearchBarBox(completion=AlbumTagCompletion(),
                              accel_group=self.accelerators)
        search.connect('query-changed', self.__update_filter)
        connect_obj(search, 'focus-out', lambda w: w.grab_focus(), view)
        self.__search = search

        prefs = PreferencesButton(self, model_sort)
        search.pack_start(prefs, False, True, 0)
        self.pack_start(Align(search, left=6, top=6), False, True, 0)
        self.pack_start(sw, True, True, 0)

        self.connect("destroy", self.__destroy)

        self.enable_row_update(view, sw, self.view)

        self.connect('key-press-event', self.__key_pressed, library.librarian)

        if app.cover_manager:
            connect_destroy(
                app.cover_manager, "cover-changed", self._cover_changed)

        self.show_all()

    def _cover_changed(self, manager, songs):
        model = self.__model
        songs = set(songs)
        for iter_, item in model.iterrows():
            album = item.album
            if album is not None and songs & album.songs:
                item.scanned = False
                model.row_changed(model.get_path(iter_), iter_)

    def __key_pressed(self, widget, event, librarian):
        if qltk.is_accel(event, "<Primary>I"):
            songs = self.__get_selected_songs()
            if songs:
                window = Information(librarian, songs, self)
                window.show()
            return True
        elif qltk.is_accel(event, "<alt>Return"):
            songs = self.__get_selected_songs()
            if songs:
                window = SongProperties(librarian, songs, self)
                window.show()
            return True
        return False

    def _row_needs_update(self, model, iter_):
        item = model.get_value(iter_)
        return item.album is not None and not item.scanned

    def _update_row(self, filter_model, iter_):
        sort_model = filter_model.get_model()
        model = sort_model.get_model()
        iter_ = filter_model.convert_iter_to_child_iter(iter_)
        iter_ = sort_model.convert_iter_to_child_iter(iter_)
        tref = Gtk.TreeRowReference.new(model, model.get_path(iter_))
        mag = config.getfloat("browsers", "covergrid_magnification", 3.)

        def callback():
            path = tref.get_path()
            if path is not None:
                model.row_changed(path, model.get_iter(path))
            # XXX: icon view seems to ignore row_changed signals for pixbufs..
            self.queue_draw()

        item = model.get_value(iter_)
        scale_factor = self.get_scale_factor() * mag
        item.scan_cover_grid(scale_factor=scale_factor,
                        callback=callback,
                        cancel=self._cover_cancel)

    def __destroy(self, browser):
        self._cover_cancel.cancel()
        self.disable_row_update()

        self.view.set_model(None)

        klass = type(browser)
        if not klass.instances():
            klass._destroy_model()

    def __update_filter(self, entry, text, scroll_up=True, restore=False):
        model = self.view.get_model()

        self.__filter = None
        query = self.__search.get_query(self.STAR)
        if not query.matches_all:
            self.__filter = query.search
        self.__bg_filter = background_filter()

        self.__inhibit()

        # If we're hiding "All Albums", then there will always
        # be something to filter ­— probably there's a better
        # way to implement this

        if (not restore or self.__filter or self.__bg_filter) or (not
            config.getboolean("browsers", "covergrid_all", False)):
            model.refilter()

        self.__uninhibit()

    def __parse_query(self, model, iter_, data):
        f, b = self.__filter, self.__bg_filter
        album = model.get_album(iter_)

        if f is None and b is None and album is not None:
            return True
        else:
            if album is None:
                return config.getboolean("browsers", "covergrid_all", False)
            elif b is None:
                return f(album)
            elif f is None:
                return b(album)
            else:
                return b(album) and f(album)

    def __search_func(self, model, column, key, iter_, data):
        album = model.get_album(iter_)
        if album is None:
            return config.getboolean("browsers", "covergrid_all", False)
        key = key.lower()
        title = album.title.lower()
        if key in title:
            return False
        if config.getboolean("browsers", "album_substrings"):
            people = (p.lower() for p in album.list("~people"))
            for person in people:
                if key in person:
                    return False
        return True

    def __rightclick(self, view, event, library):
        x = int(event.x)
        y = int(event.y)
        current_path = view.get_path_at_pos(x, y)
        if event.button == Gdk.BUTTON_SECONDARY and current_path:
            if not view.path_is_selected(current_path):
                view.unselect_all()
            view.select_path(current_path)
            self.__popup(view, library)

    def __popup(self, view, library):

        albums = self.__get_selected_albums()
        songs = self.__get_songs_from_albums(albums)

        items = []
        num = len(albums)
        button = MenuItem(
            ngettext("Reload album _cover", "Reload album _covers", num),
            Icons.VIEW_REFRESH)
        button.connect('activate', self.__refresh_album, view)
        items.append(button)

        menu = SongsMenu(library, songs, items=[items])
        menu.show_all()
        popup_menu_at_widget(menu, view,
            Gdk.BUTTON_SECONDARY,
            Gtk.get_current_event_time())

    def _show_tooltip(self, widget, x, y, keyboard_tip, tooltip):
        w = self.scrollwin.get_hadjustment().get_value()
        z = self.scrollwin.get_vadjustment().get_value()
        path = widget.get_path_at_pos(int(x + w), int(y + z))
        if path is None:
            return False
        model = widget.get_model()
        iter = model.get_iter(path)
        album = model.get_album(iter)
        if album is None:
            text = "<b>%s</b>" % _("All Albums")
            text += "\n" + ngettext("%d album",
                "%d albums", len(model) - 1) % (len(model) - 1)
            markup = text
        else:
            markup = self.display_pattern % album
        tooltip.set_markup(markup)
        return True

    def __refresh_album(self, menuitem, view):
        items = self.__get_selected_items()
        for item in items:
            item.scanned = False
        model = self.view.get_model()
        for iter_, item in model.iterrows():
            if item in items:
                model.row_changed(model.get_path(iter_), iter_)

    def __get_selected_items(self):
        model = self.view.get_model()
        paths = self.view.get_selected_items()
        return model.get_items(paths)

    def __get_selected_albums(self):
        model = self.view.get_model()
        paths = self.view.get_selected_items()
        return model.get_albums(paths)

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

    def __drag_data_get(self, view, ctx, sel, tid, etime):
        songs = self.__get_selected_songs()
        if tid == 1:
            qltk.selection_set_songs(sel, songs)
        else:
            sel.set_uris([song("~uri") for song in songs])

    def __play_selection(self, view, indices, col):
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
            self.__update_filter(self.__search, text)
            # self.__inhibit()
            #self.view.set_cursor((0,), None, False)
            # self.__uninhibit()
            self.activate()

    def get_filter_text(self):
        return self.__search.get_text()

    def can_filter(self, key):
        # Numerics are different for collections, and although title works,
        # it's not of much use here.
        if key is not None and (key.startswith("~#") or key == "title"):
            return False
        return super(CoverGrid, self).can_filter(key)

    def can_filter_albums(self):
        return True

    def list_albums(self):
        model = self.view.get_model()
        return [row[0].album.key for row in model if row[0].album]

    def select_by_func(self, func, scroll=True, one=False):
        model = self.view.get_model()
        if not model:
            return False

        selection = self.view.get_selected_items()
        first = True
        for row in model:
            if func(row):
                if not first:
                    selection.select_path(row.path)
                    continue
                self.view.unselect_all()
                self.view.select_path(row.path)
                self.view.set_cursor(row.path, None, False)
                if scroll:
                    self.view.scroll_to_path(row.path, True, 0.5, 0.5)
                first = False
                if one:
                    break
        return not first

    def filter_albums(self, values):
        self.__inhibit()
        changed = self.select_by_func(
            lambda r: r[0].album and r[0].album.key in values)
        self.__uninhibit()
        if changed:
            self.activate()

    def unfilter(self):
        self.filter_text("")
        #self.view.set_cursor((0,), None, False)

    def activate(self):
        self.view.emit('selection-changed')

    def __inhibit(self):
        self.view.handler_block(self.__sig)

    def __uninhibit(self):
        self.view.handler_unblock(self.__sig)

    def restore(self):
        text = config.gettext("browsers", "query_text")
        entry = self.__search
        entry.set_text(text)

        # update_filter expects a parsable query
        if Query(text).is_parsable:
            self.__update_filter(entry, text, scroll_up=False, restore=True)

        keys = config.gettext("browsers", "covergrid", "").split("\n")

        # FIXME: If albums is "" then it could be either all albums or
        # no albums. If it's "" and some other stuff, assume no albums,
        # otherwise all albums.
        self.__inhibit()
        if keys != [""]:

            def select_fun(row):
                album = row[0].album
                if not album:  # all
                    return False
                return album.str_key in keys
            self.select_by_func(select_fun)
        self.__uninhibit()

    def scroll(self, song):
        album_key = song.album_key
        select = lambda r: r[0].album and r[0].album.key == album_key
        self.select_by_func(select, one=True)

    def __get_config_string(self):
        model = self.view.get_model()
        paths = self.view.get_selected_items()

        # All is selected
        if model.contains_all(paths):
            return ""

        # All selected albums
        albums = model.get_albums(paths)

        confval = "\n".join((a.str_key for a in albums))
        # ConfigParser strips a trailing \n so we move it to the front
        if confval and confval[-1] == "\n":
            confval = "\n" + confval[:-1]
        return confval

    def save(self):
        conf = self.__get_config_string()
        config.settext("browsers", "covergrid", conf)
        text = self.__search.get_text()
        config.settext("browsers", "query_text", text)

    def __update_songs(self, selection):
        songs = self.__get_selected_songs(sort=False)
        self.songs_selected(songs)
