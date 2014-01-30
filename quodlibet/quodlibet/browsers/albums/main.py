# -*- coding: utf-8 -*-
# Copyright 2004-2007 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2009-2010 Steven Robertson
#           2012-2013 Nick Boultbee
#           2009-2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from __future__ import absolute_import

import os

from gi.repository import Gtk, Pango, Gdk, GLib

from .prefs import Preferences, PATTERN
from .models import AlbumModel, AlbumFilterModel, AlbumSortModel

from quodlibet import config
from quodlibet import const
from quodlibet import qltk
from quodlibet import util

from quodlibet.browsers._base import Browser
from quodlibet.parse import Query, XMLFromMarkupPattern
from quodlibet.qltk.completion import EntryWordCompletion
from quodlibet.qltk.information import Information
from quodlibet.qltk.properties import SongProperties
from quodlibet.qltk.songsmenu import SongsMenu
from quodlibet.qltk.views import AllTreeView
from quodlibet.qltk.x import MenuItem, Alignment, ScrolledWindow, RadioMenuItem
from quodlibet.qltk.x import SymbolicIconImage, SeparatorMenuItem
from quodlibet.qltk.searchbar import SearchBarBox
from quodlibet.qltk.menubutton import MenuButton
from quodlibet.util import copool, gobject_weak, thumbnails
from quodlibet.util.library import background_filter
from quodlibet.util.collection import Album
from quodlibet.qltk.cover import get_no_cover_pixbuf


PATTERN_FN = os.path.join(const.USERDIR, "album_pattern")
ALBUM_QUERIES = os.path.join(const.USERDIR, "lists", "album_queries")


class AlbumTagCompletion(EntryWordCompletion):
    def __init__(self):
        super(AlbumTagCompletion, self).__init__()
        try:
            model = self.__model
        except AttributeError:
            model = type(self).__model = Gtk.ListStore(str)
            self.__refreshmodel()
        self.set_model(model)
        self.set_text_column(0)

    def __refreshmodel(self, *args):
        for tag in ["title", "album", "date", "people", "artist", "genre"]:
            self.__model.append(row=[tag])
        for tag in ["tracks", "discs", "length", "date"]:
            self.__model.append(row=["#(" + tag])
        for tag in ["rating", "playcount", "skipcount"]:
            for suffix in ["avg", "max", "min", "sum"]:
                self.__model.append(row=["#(%s:%s" % (tag, suffix)])


def cmpa(a, b):
    """Like cmp but treats values that evaluate to false as inf"""
    if not a and b:
        return 1
    if not b and a:
        return -1
    return cmp(a, b)


class PreferencesButton(Gtk.HBox):
    def __init__(self, browser, model):
        super(PreferencesButton, self).__init__()

        sort_orders = [
            (_("_Title"), self.__compare_title),
            (_("_Artist"), self.__compare_artist),
            (_("_Date"), self.__compare_date),
            (_("_Genre"), self.__compare_genre),
            (_("_Rating"), self.__compare_rating),
        ]

        menu = Gtk.Menu()

        sort_item = Gtk.MenuItem(_("Sort _by..."), use_underline=True)
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
            gobject_weak(item.connect, "toggled",
                         util.DeferredSignal(self.__sort_toggled_cb),
                         model, i)
            sort_menu.append(item)

        sort_item.set_submenu(sort_menu)
        menu.append(sort_item)

        pref_item = MenuItem(_("_Preferences"), Gtk.STOCK_PREFERENCES)
        menu.append(pref_item)
        gobject_weak(pref_item.connect_object,
                     "activate", Preferences, browser)

        menu.show_all()

        button = MenuButton(
                SymbolicIconImage("emblem-system", Gtk.IconSize.MENU),
                arrow=True)
        button.set_menu(menu)
        self.pack_start(button, True, True, 0)

    def __sort_toggled_cb(self, item, model, num):
        if item.get_active():
            config.set("browsers", "album_sort", str(num))
            model.set_sort_column_id(100 + num, Gtk.SortType.ASCENDING)

    def __compare_title(self, model, i1, i2, data):
        a1, a2 = model.get_value(i1, 0), model.get_value(i2, 0)
        # all albums has to stay at the top
        if (a1 and a2) is None:
            return cmp(a1, a2)
        # move album without a title to the bottom
        if not a1.title:
            return 1
        if not a2.title:
            return -1
        return (cmpa(a1.sort, a2.sort) or
                cmp(a1.key, a2.key))

    def __compare_artist(self, model, i1, i2, data):
        a1, a2 = model.get_value(i1, 0), model.get_value(i2, 0)
        if (a1 and a2) is None:
            return cmp(a1, a2)
        if not a1.title:
            return 1
        if not a2.title:
            return -1
        return (cmpa(a1.peoplesort, a2.peoplesort) or
                cmpa(a1.date, a2.date) or
                cmpa(a1.sort, a2.sort) or
                cmp(a1.key, a2.key))

    def __compare_date(self, model, i1, i2, data):
        a1, a2 = model.get_value(i1, 0), model.get_value(i2, 0)
        if (a1 and a2) is None:
            return cmp(a1, a2)
        if not a1.title:
            return 1
        if not a2.title:
            return -1
        return (cmpa(a1.date, a2.date) or
                cmpa(a1.sort, a2.sort) or
                cmp(a1.key, a2.key))

    def __compare_genre(self, model, i1, i2, data):
        a1, a2 = model.get_value(i1, 0), model.get_value(i2, 0)
        if (a1 and a2) is None:
            return cmp(a1, a2)
        if not a1.title:
            return 1
        if not a2.title:
            return -1
        return (cmpa(a1.genre, a2.genre) or
                cmpa(a1.peoplesort, a2.peoplesort) or
                cmpa(a1.date, a2.date) or
                cmpa(a1.sort, a2.sort) or
                cmp(a1.key, a2.key))

    def __compare_rating(self, model, i2, i1, data):
        a1, a2 = model.get_value(i1, 0), model.get_value(i2, 0)
        if (a1 and a2) is None:
            return cmp(a1, a2)
        return (cmpa(a1("~#rating"), a2("~#rating")) or
                cmpa(a1.date, a2.date) or
                cmpa(a1.sort, a2.sort) or
                cmp(a1.key, a2.key))


class VisibleUpdate(object):

    # how many rows should be updated
    # beyond the visible area in both directions
    PRELOAD_COUNT = 35

    def enable_row_update(self, view, sw, column):
        gobject_weak(view.connect_object, 'draw',
                     self.__update_visibility, view)

        gobject_weak(sw.get_vadjustment().connect, "value-changed",
                     self.__stop_update, view, parent=view)

        self.__pending_paths = []
        self.__scan_timeout = None
        self.__column = column
        self.__first_expose = True

    def disable_row_update(self):
        if self.__scan_timeout:
            GLib.source_remove(self.__scan_timeout)
            self.__scan_timeout = None

        if self.__pending_paths:
            copool.remove(self.__scan_paths)

        self.__column = None
        self.__pending_paths = []

    def _row_needs_update(self, row):
        """Should return True if the rows should be updated"""
        raise NotImplementedError

    def _update_row(self, row):
        """Do whatever is needed to update the row"""
        raise NotImplementedError

    def __stop_update(self, adj, view):
        if self.__pending_paths:
            copool.remove(self.__scan_paths)
            self.__pending_paths = []
            self.__update_visibility(view)

    def __update_visibility(self, view, *args):
        if not self.__column.get_visible():
            return

        # update all visible rows on first expose event
        if self.__first_expose:
            self.__first_expose = False
            self.__update_visible_rows(view, 0)
            for i in self.__scan_paths():
                pass

        if self.__scan_timeout:
            GLib.source_remove(self.__scan_timeout)
            self.__scan_timeout = None

        self.__scan_timeout = GLib.timeout_add(
            50, self.__update_visible_rows, view, self.PRELOAD_COUNT)

    def __scan_paths(self):
        while self.__pending_paths:
            model, path = self.__pending_paths.pop()
            try:
                row = model[path]
            # row could have gone away by now
            except IndexError:
                pass
            else:
                self._update_row(row)
                yield True

    def __update_visible_rows(self, view, preload):
        vrange = view.get_visible_range()
        if vrange is None:
            return

        model_filter = view.get_model()
        model = model_filter.get_model()

        #generate a path list so that cover scanning starts in the middle
        #of the visible area and alternately moves up and down
        start, end = vrange

        # pygtk2.12 sometimes returns empty tuples
        if not start or not end:
            return

        start = start.get_indices()[0] - preload - 1
        end = end.get_indices()[0] + preload

        vlist = range(end, start, -1)
        top = vlist[:len(vlist) / 2]
        bottom = vlist[len(vlist) / 2:]
        top.reverse()

        vlist_new = []
        for i in vlist:
            if top:
                vlist_new.append(top.pop())
            if bottom:
                vlist_new.append(bottom.pop())
        vlist_new = filter(lambda s: s >= 0, vlist_new)

        vlist_new = map(Gtk.TreePath, vlist_new)

        visible_paths = []
        for path in vlist_new:
            model_path = model_filter.convert_path_to_child_path(path)
            try:
                row = model[model_path]
            except TypeError:
                pass
            else:
                if self._row_needs_update(row):
                    visible_paths.append([model, model_path])

        if not self.__pending_paths and visible_paths:
            copool.add(self.__scan_paths)
        self.__pending_paths = visible_paths


class AlbumList(Browser, Gtk.VBox, util.InstanceTracker, VisibleUpdate):
    __gsignals__ = Browser.__gsignals__
    __model = None
    __no_cover = None
    __last_render = None
    __last_render_pb = None

    name = _("Album List")
    accelerated_name = _("_Album List")
    priority = 4

    def pack(self, songpane):
        container = qltk.RHPaned()
        container.pack1(self, True, False)
        container.pack2(songpane, True, False)
        return container

    def unpack(self, container, songpane):
        container.remove(songpane)
        container.remove(self)

    @classmethod
    def init(klass, library):
        try:
            text = file(PATTERN_FN).read().rstrip()
            #Migrate <=2.2 pattern.
            #This breaks people, title.. so remove it someday.
            text = text.replace("<people", "<~people")
            text = text.replace("<title", "<album")
            klass._pattern_text = text
        except EnvironmentError:
            klass._pattern_text = PATTERN

        cover_size = Album.COVER_SIZE
        klass.__no_cover = get_no_cover_pixbuf(cover_size, cover_size)
        klass._pattern = XMLFromMarkupPattern(klass._pattern_text)

    @classmethod
    def _destroy_model(klass):
        klass.__model.destroy()
        klass.__model = None

    @classmethod
    def toggle_covers(klass):
        on = config.getboolean("browsers", "album_covers")
        for albumlist in klass.instances():
            albumlist.__cover_column.set_visible(on)
            for column in albumlist.view.get_columns():
                column.queue_resize()

    @classmethod
    def refresh_pattern(klass, pattern_text):
        if pattern_text == klass._pattern_text:
            return
        klass._pattern_text = pattern_text
        klass._pattern = XMLFromMarkupPattern(pattern_text)
        klass.__model.refresh_all()
        pattern_fn = PATTERN_FN
        f = file(pattern_fn, "w")
        f.write(pattern_text + "\n")
        f.close()

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

    def __init__(self, library, main):
        super(AlbumList, self).__init__(spacing=6)
        self._register_instance()
        if self.__model is None:
            self._init_model(library)

        sw = ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.IN)
        self.view = view = AllTreeView()
        view.set_headers_visible(False)
        model_sort = AlbumSortModel(model=self.__model)
        model_filter = AlbumFilterModel(child_model=model_sort)

        self.__bg_filter = background_filter()
        self.__filter = None
        model_filter.set_visible_func(self.__parse_query)

        render = Gtk.CellRendererPixbuf()
        self.__cover_column = column = Gtk.TreeViewColumn("covers", render)
        column.set_visible(config.getboolean("browsers", "album_covers"))
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column.set_fixed_width(Album.COVER_SIZE + 12)
        render.set_property('height', Album.COVER_SIZE + 8)

        def cell_data_pb(column, cell, model, iter_, no_cover):
            album = model.get_album(iter_)
            if album is None:
                pixbuf = None
            elif album.cover:
                pixbuf = album.cover
            else:
                pixbuf = no_cover
            if self.__last_render_pb == pixbuf:
                return
            self.__last_render_pb = pixbuf
            cell.set_property('pixbuf', pixbuf)

        column.set_cell_data_func(render, cell_data_pb, self.__no_cover)
        view.append_column(column)

        render = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("albums", render)
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        render.set_property('ellipsize', Pango.EllipsizeMode.END)

        def cell_data(column, cell, model, iter_, data):
            album = model.get_album(iter_)

            if album is None:
                text = "<b>%s</b>" % _("All Albums")
                text += "\n" + ngettext("%d album", "%d albums",
                        len(model) - 1) % (len(model) - 1)
                markup = text
            else:
                markup = AlbumList._pattern % album

            if self.__last_render == markup:
                return
            self.__last_render = markup
            cell.markup = markup
            cell.set_property('markup', markup)

        column.set_cell_data_func(render, cell_data)
        view.append_column(column)

        view.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        view.set_rules_hint(True)
        view.set_search_equal_func(self.__search_func, None)
        view.set_search_column(0)
        view.set_model(model_filter)
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.add(view)

        if main:
            gobject_weak(view.connect, 'row-activated',
                         self.__play_selection)

        self.__sig = gobject_weak(
            view.get_selection().connect, 'changed',
            util.DeferredSignal(self.__update_songs), parent=view)

        targets = [("text/x-quodlibet-songs", Gtk.TargetFlags.SAME_APP, 1),
                   ("text/uri-list", 0, 2)]
        targets = [Gtk.TargetEntry.new(*t) for t in targets]

        view.drag_source_set(
            Gdk.ModifierType.BUTTON1_MASK, targets, Gdk.DragAction.COPY)
        gobject_weak(view.connect, "drag-data-get", self.__drag_data_get)
        gobject_weak(view.connect_object, 'popup-menu',
                     self.__popup, view, library)

        self.accelerators = Gtk.AccelGroup()
        search = SearchBarBox(completion=AlbumTagCompletion(),
                              accel_group=self.accelerators)
        gobject_weak(search.connect, 'query-changed', self.__update_filter)
        gobject_weak(search.connect_object,
                     'focus-out', lambda w: w.grab_focus(), view)
        self.__search = search

        prefs = PreferencesButton(self, model_sort)
        search.pack_start(prefs, False, True, 0)
        if main:
            self.pack_start(Alignment(search, left=6, top=6), False, True, 0)
        else:
            self.pack_start(search, False, True, 0)

        self.pack_start(sw, True, True, 0)

        self.connect("destroy", self.__destroy)

        self.enable_row_update(view, sw, self.__cover_column)

        self.connect('key-press-event', self.__key_pressed, library.librarian)

        self.show_all()

    def __key_pressed(self, widget, event, librarian):
        if qltk.is_accel(event, "<ctrl>I"):
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

    def _row_needs_update(self, row):
        album = row[0]
        return album is not None and not album.scanned

    def _update_row(self, row):
        album = row[0]
        album.scan_cover()
        self._refresh_albums([album])

    def __destroy(self, browser):
        self.disable_row_update()

        self.__inhibit()
        self.view.set_model(None)

        klass = type(browser)
        if not klass.instances():
            klass._destroy_model()

    def __update_filter(self, entry, text, scroll_up=True, restore=False):
        model = self.view.get_model()

        self.__filter = None
        if not Query.match_all(text):
            self.__filter = Query(text, star=["~people", "album"]).search
        self.__bg_filter = background_filter()

        self.__inhibit()

        # We could be smart and try to scroll to a selected album
        # but that introduces lots of wild scrolling. Feel free to change it.
        # Without scrolling the TV trys to stay at the same position (40% down)
        # which makes no sence so always go to the top.
        if scroll_up:
            self.view.scroll_to_point(0, 0)

        # don't filter on restore if there is nothing to filter
        if not restore or self.__filter or self.__bg_filter:
            model.refilter()

        self.__uninhibit()

    def __parse_query(self, model, iter_, data):
        f, b = self.__filter, self.__bg_filter

        if f is None and b is None:
            return True
        else:
            album = model.get_album(iter_)
            if album is None:
                return True
            elif b is None:
                return f(album)
            elif f is None:
                return b(album)
            else:
                return b(album) and f(album)

    def __search_func(self, model, column, key, iter_, data):
        album = model.get_album(iter_)
        if album is None:
            return True
        key = key.decode('utf-8').lower()
        title = album.title.lower()
        if key in title:
            return False
        if config.getboolean("browsers", "album_substrings"):
            people = (p.lower() for p in album.list("~people"))
            for person in people:
                if key in person:
                    return False
        return True

    def __popup(self, view, library):
        albums = self.__get_selected_albums()
        songs = self.__get_songs_from_albums(albums)
        menu = SongsMenu(library, songs, parent=self)

        if self.__cover_column.get_visible():
            num = len(albums)
            button = MenuItem(
                ngettext("Reload album _cover", "Reload album _covers", num),
                Gtk.STOCK_REFRESH)
            gobject_weak(button.connect, 'activate',
                self.__refresh_album, view)
            menu.prepend(SeparatorMenuItem())
            menu.prepend(button)

        menu.show_all()
        return view.popup_menu(menu, 0, Gtk.get_current_event_time())

    def __refresh_album(self, menuitem, view):
        albums = self.__get_selected_albums()
        for album in albums:
            album.scan_cover(True)
        self._refresh_albums(albums)

    def __get_selected_albums(self):
        selection = self.view.get_selection()
        model, paths = selection.get_selected_rows()
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
        self.emit("activated")

    def active_filter(self, song):
        for album in self.__get_selected_albums():
            if song in album.songs:
                return True
        return False

    def can_filter_text(self):
        return True

    def filter_text(self, text):
        self.__search.set_text(text)
        if Query.is_parsable(text):
            self.__update_filter(self.__search, text)
            self.__inhibit()
            self.view.set_cursor((0,))
            self.__uninhibit()
            self.activate()

    def can_filter(self, key):
        # numerics are different for collections, and title
        # works, but not of much use here
        if key is not None and (key.startswith("~#") or key == "title"):
            return False
        return super(AlbumList, self).can_filter(key)

    def can_filter_albums(self):
        return True

    def list_albums(self):
        model = self.view.get_model()
        return [row[0].key for row in model if row[0]]

    def filter_albums(self, values):
        view = self.view
        self.__inhibit()
        changed = view.select_by_func(lambda r: r[0] and r[0].key in values)
        self.__uninhibit()
        if changed:
            self.activate()

    def unfilter(self):
        self.filter_text("")
        self.view.set_cursor((0,))

    def activate(self):
        self.view.get_selection().emit('changed')

    def __inhibit(self):
        self.view.get_selection().handler_block(self.__sig)

    def __uninhibit(self):
        self.view.get_selection().handler_unblock(self.__sig)

    def restore(self):
        text = config.get("browsers", "query_text").decode("utf-8")
        entry = self.__search
        entry.set_text(text)

        # update_filter expects a parsable query
        if Query.is_parsable(text):
            self.__update_filter(entry, text, scroll_up=False, restore=True)

        keys = config.get("browsers", "albums").split("\n")

        # FIXME: If albums is "" then it could be either all albums or
        # no albums. If it's "" and some other stuff, assume no albums,
        # otherwise all albums.
        self.__inhibit()
        if keys == [""]:
            self.view.set_cursor((0,))
        else:

            def select_fun(row):
                album = row[0]
                if not album:  # all
                    return False
                return album.str_key in keys
            self.view.select_by_func(select_fun)
        self.__uninhibit()

    def scroll(self, song):
        album_key = song.album_key
        select = lambda r: r[0] and r[0].key == album_key
        self.view.select_by_func(select, one=True)

    def __get_config_string(self):
        selection = self.view.get_selection()
        model, paths = selection.get_selected_rows()

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
        config.set("browsers", "albums", conf)
        text = self.__search.get_text().encode("utf-8")
        config.set("browsers", "query_text", text)

    def __update_songs(self, selection):
        songs = self.__get_selected_songs(sort=False)
        self.emit('songs-selected', songs, None)
