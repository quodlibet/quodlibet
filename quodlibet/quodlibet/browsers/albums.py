# -*- coding: utf-8 -*-
# Copyright 2004-2010 Joe Wreschnig, Michael Urman, Iñigo Serna,
#                     Christoph Reiter, Steven Robertson
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

from gi.repository import Gtk, Pango, Gdk, GLib

from quodlibet import config
from quodlibet import const
from quodlibet import qltk
from quodlibet import util

from quodlibet.browsers._base import Browser
from quodlibet.parse import Query, XMLFromPattern
from quodlibet.qltk.ccb import ConfigCheckButton
from quodlibet.qltk.completion import EntryWordCompletion
from quodlibet.qltk.information import Information
from quodlibet.qltk.properties import SongProperties
from quodlibet.qltk.songsmenu import SongsMenu
from quodlibet.qltk.textedit import PatternEditBox
from quodlibet.qltk.views import AllTreeView
from quodlibet.qltk.x import MenuItem, Alignment, ScrolledWindow, RadioMenuItem
from quodlibet.qltk.x import SymbolicIconImage
from quodlibet.qltk.searchbar import SearchBarBox
from quodlibet.qltk.menubutton import MenuButton
from quodlibet.util import copool, gobject_weak, thumbnails
from quodlibet.util.library import background_filter
from quodlibet.util.collection import Album
from quodlibet.qltk.models import SingleObjectStore

EMPTY = _("Songs not in an album")
PATTERN = r"""\<b\><album|\<i\><album>\</i\>|%s>\</b\><date| (<date>)>
\<small\><~discs|<~discs> - ><~tracks> - <~long-length>\</small\>
<~people>""" % EMPTY
PATTERN_FN = os.path.join(const.USERDIR, "album_pattern")
ALBUM_QUERIES = os.path.join(const.USERDIR, "lists", "album_queries")


class FakeAlbum(dict):
    def get(self, key, default="", connector=" - "):
        if key[:1] == "~" and '~' in key[1:]:
            return connector.join(map(self.get, util.tagsplit(key)))
        elif key[:2] == "~#" and key[-4:-3] == ":":
            func = key[-3:]
            key = key[:-4]
            return "%s<%s>" % (util.tag(key), func)
        elif key in self:
            return self[key]
        return util.tag(key)

    __call__ = get

    def comma(self, key):
        value = self.get(key)
        if isinstance(value, (int, float)):
            return value
        return value.replace("\n", ", ")


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


class Preferences(qltk.UniqueWindow):
    def __init__(self, parent):
        if self.is_not_unique():
            return
        super(Preferences, self).__init__()
        self.set_border_width(12)
        self.set_title(_("Album List Preferences") + " - Quod Libet")
        self.set_default_size(400, 270)
        self.set_transient_for(qltk.get_top_parent(parent))

        box = Gtk.VBox(spacing=6)

        cb = ConfigCheckButton(
            _("Show album _covers"), "browsers", "album_covers")
        cb.set_active(config.getboolean("browsers", "album_covers"))
        gobject_weak(cb.connect, 'toggled',
                     lambda s: AlbumList.toggle_covers())
        box.pack_start(cb, False, True, 0)

        cb = ConfigCheckButton(
            _("Inline _search includes people"),
            "browsers", "album_substrings")
        cb.set_active(config.getboolean("browsers", "album_substrings"))
        box.pack_start(cb, False, True, 0)

        vbox = Gtk.VBox(spacing=6)
        label = Gtk.Label()
        label.set_alignment(0.0, 0.5)
        edit = PatternEditBox(PATTERN)
        edit.text = AlbumList._pattern_text
        gobject_weak(edit.apply.connect, 'clicked', self.__set_pattern, edit)
        gobject_weak(edit.buffer.connect_object, 'changed',
            self.__preview_pattern, edit, label, parent=edit)

        vbox.pack_start(label, False, True, 0)
        vbox.pack_start(edit, True, True, 0)
        self.__preview_pattern(edit, label)
        f = qltk.Frame(_("Album Display"), child=vbox)
        box.pack_start(f, True, True, 0)

        main_box = Gtk.VBox(spacing=12)
        close = Gtk.Button(stock=Gtk.STOCK_CLOSE)
        close.connect('clicked', lambda *x: self.destroy())
        b = Gtk.HButtonBox()
        b.set_layout(Gtk.ButtonBoxStyle.END)
        b.pack_start(close, True, True, 0)

        main_box.pack_start(box, True, True, 0)
        main_box.pack_start(b, False, True, 0)
        self.add(main_box)

        close.grab_focus()
        self.show_all()

    def __set_pattern(self, apply, edit):
        AlbumList.refresh_pattern(edit.text)

    def __preview_pattern(self, edit, label):
        people = "\n".join(
            [util.tag("artist"), util.tag("performer"), util.tag("arranger")])
        album = FakeAlbum({
            "date": "2004-10-31",
            "~length": util.format_time(6319),
            "~long-length": util.format_time_long(6319),
            "~tracks": ngettext("%d track", "%d tracks", 5) % 5,
            "~discs": ngettext("%d disc", "%d discs", 2) % 2,
            "~people": people})

        try:
            text = XMLFromPattern(edit.text) % album
        except:
            text = _("Invalid pattern")
            edit.apply.set_sensitive(False)
        try:
            Pango.parse_markup(text, -1, u"\u0000")
        except GLib.GError:
            text = _("Invalid pattern")
            edit.apply.set_sensitive(False)
        else:
            edit.apply.set_sensitive(True)
        label.set_markup(text)


def cmpa(a, b):
    """Like cmp but treats values that evaluate to false as inf"""
    if not a and b:
        return 1
    if not b and a:
        return -1
    return cmp(a, b)


class PreferencesButton(Gtk.HBox):
    def __init__(self, model):
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
        gobject_weak(pref_item.connect_object, "activate", Preferences, self)

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
        a1, a2 = model[i1][0], model[i2][0]
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
        a1, a2 = model[i1][0], model[i2][0]
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
        a1, a2 = model[i1][0], model[i2][0]
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
        a1, a2 = model[i1][0], model[i2][0]
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
        a1, a2 = model[i1][0], model[i2][0]
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

        theme = Gtk.IconTheme.get_default()
        cover_size = Album.COVER_SIZE
        try:
            klass.__no_cover = theme.load_icon(
                "quodlibet-missing-cover", cover_size, 0)
        except GLib.GError:
            pass
        else:
            klass.__no_cover = thumbnails.scale(
                klass.__no_cover, (cover_size, cover_size))

        klass._pattern = XMLFromPattern(klass._pattern_text)

    @classmethod
    def _destroy_model(klass):
        library = klass.__library
        for sig in klass.__sigs:
            library.albums.disconnect(sig)
        klass.__library = None
        klass.__model.clear()
        klass.__model = None

    @classmethod
    def toggle_covers(klass):
        on = config.getboolean("browsers", "album_covers")
        for albumlist in klass.instances():
            albumlist.__cover_column.set_visible(on)
            map(lambda x: x.queue_resize(), albumlist.view.get_columns())

    @classmethod
    def refresh_pattern(klass, pattern_text):
        if pattern_text == klass._pattern_text:
            return
        klass._pattern_text = pattern_text
        klass._pattern = XMLFromPattern(pattern_text)
        for row in klass.__model:
            klass.__model.row_changed(row.path, row.iter)
        pattern_fn = os.path.join(const.USERDIR, "album_pattern")
        f = file(pattern_fn, "w")
        f.write(pattern_text + "\n")
        f.close()

    @classmethod
    def _init_model(klass, library):
        klass.__model = model = SingleObjectStore(object)
        klass.__library = library
        library.albums.load()
        klass.__sigs = [
            library.albums.connect("added", klass._add_albums, model),
            library.albums.connect("removed", klass._remove_albums, model),
            library.albums.connect("changed", klass._change_albums, model)]
        model.append(row=[None])
        model.append_many(library.albums.itervalues())

    @classmethod
    def _refresh_albums(klass, albums):
        """We signal all other open album views that we changed something
        (Only needed for the cover atm) so they redraw as well."""
        if klass.__library:
            klass.__library.albums.refresh(albums)

    @classmethod
    def _add_albums(klass, library, added, model):
        for album in added:
            model.append(row=[album])

    @classmethod
    def _remove_albums(klass, library, removed, model):
        removed_albums = removed.copy()
        for row in model:
            if row[0] and row[0] in removed_albums:
                removed_albums.remove(row[0])
                model.remove(row.iter)
                if not removed_albums:
                    break

    @classmethod
    def _change_albums(klass, library, changed, model):
        """Trigger a row redraw for each album that changed"""
        changed_albums = changed.copy()
        for row in model:
            if row[0] and row[0] in changed_albums:
                changed_albums.remove(row[0])
                model.row_changed(row.path, row.iter)
                if not changed_albums:
                    break

    def __init__(self, library, main):
        super(AlbumList, self).__init__(spacing=6)
        self._register_instance()
        if self.__model is None:
            self._init_model(library)

        sw = ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.IN)
        self.view = view = AllTreeView()
        view.set_headers_visible(False)
        model_sort = Gtk.TreeModelSort(model=self.__model)
        model_filter = model_sort.filter_new()

        self.__bg_filter = background_filter()
        self.__filter = None
        model_filter.set_visible_func(self.__parse_query)

        render = Gtk.CellRendererPixbuf()
        self.__cover_column = column = Gtk.TreeViewColumn("covers", render)
        column.set_visible(config.getboolean("browsers", "album_covers"))
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column.set_fixed_width(Album.COVER_SIZE + 12)
        render.set_property('height', Album.COVER_SIZE + 8)

        def cell_data_pb(column, cell, model, iter, no_cover):
            album = model[iter][0]
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

        def cell_data(column, cell, model, iter, data):
            album = model[iter][0]
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

        prefs = PreferencesButton(model_sort)
        search.pack_start(prefs, False, True, 0)
        if main:
            self.pack_start(Alignment(search, left=3, top=6), False, True, 0)
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

    def __parse_query(self, model, iter, data):
        f, b = self.__filter, self.__bg_filter
        if f is None and b is None:
            return True
        elif model[iter][0] is None:
            return True
        elif b is None:
            return f(model[iter][0])
        elif f is None:
            return b(model[iter][0])
        else:
            return b(model[iter][0]) and f(model[iter][0])

    def __search_func(self, model, column, key, iter, data):
        album = model[iter][0]
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
        selection = view.get_selection()
        albums = self.__get_selected_albums(selection)
        songs = self.__get_songs_from_albums(albums)
        menu = SongsMenu(library, songs, parent=self)

        if self.__cover_column.get_visible():
            num = len(albums)
            button = MenuItem(
                ngettext("Reload album _cover", "Reload album _covers", num),
                Gtk.STOCK_REFRESH)
            gobject_weak(button.connect, 'activate',
                self.__refresh_album, view)
            menu.prepend(Gtk.SeparatorMenuItem())
            menu.prepend(button)

        menu.show_all()
        return view.popup_menu(menu, 0, Gtk.get_current_event_time())

    def __refresh_album(self, menuitem, view):
        selection = view.get_selection()
        albums = self.__get_selected_albums(selection)
        for album in albums:
            album.scan_cover(True)
        self._refresh_albums(albums)

    def __get_selected_albums(self, selection):
        if not selection:
            return []
        model, rows = selection.get_selected_rows()
        if not model or not rows:
            return []
        if rows and model[rows[0]][0] is None:
            return [row[0] for row in model if row[0]]
        return [model[row][0] for row in rows]

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
        albums = self.__get_selected_albums(self.view.get_selection())
        return self.__get_songs_from_albums(albums, sort)

    def __drag_data_get(self, view, ctx, sel, tid, etime):
        songs = self.__get_selected_songs()
        if tid == 1:
            filenames = [song("~filename") for song in songs]
            type_ = Gdk.atom_intern("text/x-quodlibet-songs", True)
            sel.set(type_, 8, "\x00".join(filenames))
        else:
            sel.set_uris([song("~uri") for song in songs])

    def __play_selection(self, view, indices, col):
        self.emit("activated")

    def active_filter(self, song):
        selection = self.view.get_selection()
        for album in self.__get_selected_albums(selection):
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

        albums = config.get("browsers", "albums").split("\n")

        # FIXME: If albums is "" then it could be either all albums or
        # no albums. If it's "" and some other stuff, assume no albums,
        # otherwise all albums.
        self.__inhibit()
        if albums == [""]:
            self.view.set_cursor((0,))
        else:
            select = lambda r: r[0] and r[0].title in albums
            self.view.select_by_func(select)
        self.__uninhibit()

    def scroll(self, song):
        album_key = song.album_key
        select = lambda r: r[0] and r[0].key == album_key
        self.view.select_by_func(select, one=True)

    def __get_config_string(self, selection):
        if not selection:
            return ""
        model, rows = selection.get_selected_rows()
        if not model or not rows:
            return ""

        # All is selected
        if rows and model[rows[0]][0] is None:
            return ""

        # All selected albums
        albums = (model[row][0] for row in rows)
        # FIXME: title is far from perfect here
        confval = "\n".join((a.title for a in albums))
        # ConfigParser strips a trailing \n so we move it to the front
        if confval and confval[-1] == "\n":
            confval = "\n" + confval[:-1]
        return confval

    def save(self):
        selection = self.view.get_selection()
        conf = self.__get_config_string(selection)
        config.set("browsers", "albums", conf)
        text = self.__search.get_text().encode("utf-8")
        config.set("browsers", "query_text", text)

    def __update_songs(self, selection):
        songs = self.__get_selected_songs(sort=False)
        self.emit('songs-selected', songs, None)

browsers = [AlbumList]
