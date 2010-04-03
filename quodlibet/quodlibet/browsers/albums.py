# -*- coding: utf-8 -*-
# Copyright 2004-2010 Joe Wreschnig, Michael Urman, Iñigo Serna,
#                     Christoph Reiter, Steven Robertson
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

import gobject
import gtk
import pango

from quodlibet import config
from quodlibet import const
from quodlibet import qltk
from quodlibet import util
from quodlibet import stock

from quodlibet.browsers._base import Browser
from quodlibet.browsers.search import BoxSearchBar
from quodlibet.parse import Query, XMLFromPattern
from quodlibet.qltk.ccb import ConfigCheckButton
from quodlibet.qltk.completion import EntryWordCompletion
from quodlibet.qltk.songsmenu import SongsMenu
from quodlibet.qltk.textedit import PatternEditBox
from quodlibet.qltk.views import AllTreeView
from quodlibet.util import copool

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
        if isinstance(value, (int, float)): return value
        return value.replace("\n", ", ")

class AlbumTagCompletion(EntryWordCompletion):
    def __init__(self):
        super(AlbumTagCompletion, self).__init__()
        try: model = self.__model
        except AttributeError:
            model = type(self).__model = gtk.ListStore(str)
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
        if self.is_not_unique(): return
        super(Preferences, self).__init__()
        self.set_border_width(12)
        self.set_title(_("Album List Preferences") + " - Quod Libet")
        self.add(gtk.VBox(spacing=6))
        self.set_default_size(300, 250)
        self.set_transient_for(qltk.get_top_parent(parent))

        cb = ConfigCheckButton(
            _("Show album _covers"), "browsers", "album_covers")
        cb.set_active(config.getboolean("browsers", "album_covers"))
        cb.connect('toggled', lambda s: AlbumList.toggle_covers())
        self.child.pack_start(cb, expand=False)

        cb = ConfigCheckButton(
            _("Inline _search includes people"),
            "browsers", "album_substrings")
        cb.set_active(config.getboolean("browsers", "album_substrings"))
        self.child.pack_start(cb, expand=False)

        vbox = gtk.VBox(spacing=6)
        label = gtk.Label()
        label.set_alignment(0.0, 0.5)
        edit = PatternEditBox(PATTERN)
        edit.text = AlbumList._pattern_text
        edit.apply.connect('clicked', self.__set_pattern, edit)
        edit.buffer.connect_object(
            'changed', self.__preview_pattern, edit, label)
        vbox.pack_start(label, expand=False)
        vbox.pack_start(edit)
        self.__preview_pattern(edit, label)
        f = qltk.Frame(_("Album Display"), child=vbox)
        self.child.pack_start(f)

        self.show_all()

    def __set_pattern(self, apply, edit):
        AlbumList.refresh_pattern(edit.text)

    def __preview_pattern(self, edit, label):
        people = "\n".join(
            [util.tag("artist"), util.tag("performer"), util.tag("arranger")])
        album = FakeAlbum({"date": "2004-10-31",
            "~length": util.format_time(6319),
            "~long-length": util.format_time_long(6319),
            "~tracks": ngettext("%d track", "%d tracks", 5) % 5,
            "~discs": ngettext("%d disc", "%d discs", 2) % 2,
            "~people": people})

        try: text = XMLFromPattern(edit.text) % album
        except:
            text = _("Invalid pattern")
            edit.apply.set_sensitive(False)
        try: pango.parse_markup(text, u"\u0000")
        except gobject.GError:
            text = _("Invalid pattern")
            edit.apply.set_sensitive(False)
        else: edit.apply.set_sensitive(True)
        label.set_markup(text)

class AlbumList(Browser, gtk.VBox, util.InstanceTracker):
    expand = qltk.RHPaned
    __gsignals__ = Browser.__gsignals__
    __model = None
    __no_cover = None

    name = _("Album List")
    accelerated_name = _("_Album List")
    priority = 4

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

        no_cover = os.path.join(const.IMAGEDIR, stock.NO_COVER)
        try:
            klass.__no_cover = gtk.gdk.pixbuf_new_from_file_at_size(
                no_cover + ".svg", 48, 48)
        except gobject.GError:
            klass.__no_cover = gtk.gdk.pixbuf_new_from_file_at_size(
                no_cover + ".png", 48, 48)

        klass._pattern = XMLFromPattern(klass._pattern_text)

    @classmethod
    def toggle_covers(klass):
        on = config.getboolean("browsers", "album_covers")
        for albumlist in klass.instances():
            albumlist.__cover_column.set_visible(on)
            albumlist.__column.queue_resize()

    @classmethod
    def refresh_pattern(klass, pattern_text):
        if pattern_text == klass._pattern_text: return
        klass._pattern_text = pattern_text
        klass._pattern = XMLFromPattern(pattern_text)
        for row in klass.__model:
            klass.__model.row_changed(row.path, row.iter)
        pattern_fn = os.path.join(const.USERDIR, "album_pattern")
        f = file(pattern_fn, "w")
        f.write(pattern_text  + "\n")
        f.close()

    @classmethod
    def _init_model(klass, library):
        klass.__model = model = gtk.ListStore(object)
        klass.__library = library
        library.albums.load()
        library.albums.connect("added", klass._add_albums, model)
        library.albums.connect("removed", klass._remove_albums, model)
        library.albums.connect("changed", klass._change_albums, model)
        model.append(row=[None])
        for album in library.albums.itervalues():
            model.append(row=[album])

    @classmethod
    def _refresh_albums(klass, albums):
        """We signal all other open album views that we changed something
        (Only needed for the cover atm) so they redraw as well."""
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
                if not removed_albums: break

    @classmethod
    def _change_albums(klass, library, changed, model):
        """Trigger a row redraw for each album that changed"""
        changed_albums = changed.copy()
        for row in model:
            if row[0] and row[0] in changed:
                changed_albums.remove(row[0])
                model.row_changed(row.path, row.iter)
                if not changed_albums: break

    class FilterBar(BoxSearchBar):
        """The search filter entry HBox, modifiedto toggle between the search
        bar and album list on mnemonic activation."""
        def __init__(self, albumlist, *args, **kwargs):
            super(AlbumList.FilterBar, self).__init__(*args, **kwargs)
            self.albumlist = albumlist

        def _mnemonic_activate(self, label, group_cycling):
            widget = label.get_mnemonic_widget()
            if widget.is_focus():
                self.albumlist.view.grab_focus()
                return True

    class SortCombo(gtk.ComboBox):
        """ComboBox which sets the sort function on a TreeModelSort."""
        def __init__(self, model):
            # Contains string to display, function to do sorting
            cbmodel = gtk.ListStore(str)
            gtk.ComboBox.__init__(self, cbmodel)
            cell = gtk.CellRendererText()
            self.pack_start(cell, True)
            self.add_attribute(cell, 'text', 0)
            model.set_sort_func(100, self.__compare_title)
            model.set_sort_func(101, self.__compare_artist)
            model.set_sort_func(102, self.__compare_date)

            for text in [_("Title"), _("Artist"), _("Date")]:
                cbmodel.append(row=[text])

            self.connect_object('changed', self.__set_cmp_func, model)
            try: active = config.getint('browsers', 'album_sort')
            except: active = 0
            self.set_active(active)

        def __set_cmp_func(self, model):
            active = self.get_active()
            config.set("browsers", "album_sort", str(active))
            model.set_sort_column_id(100 + active, gtk.SORT_ASCENDING)

        def __compare_title(self, model, i1, i2):
            a1, a2 = model[i1][0], model[i2][0]
            if (a1 and a2) is None: return cmp(a1, a2)
            elif not a1.sort: return 1
            elif not a2.sort: return -1
            else: return cmp((a1.sort, a1.key), (a2.sort, a2.key))

        def __compare_artist(self, model, i1, i2):
            a1, a2 = model[i1][0], model[i2][0]
            if (a1 and a2) is None: return cmp(a1, a2)
            elif not a1.sort: return 1
            elif not a2.sort: return -1
            elif not a1.peoplesort and a2.peoplesort: return 1
            elif not a2.peoplesort and a1.peoplesort: return -1
            else: return (cmp(a1.peoplesort and a1.peoplesort[0],
                              a2.peoplesort and a2.peoplesort[0]) or
                          cmp(a1.date or "ZZZZ", a2.date or "ZZZZ") or
                          cmp((a1.sort, a1.key), (a2.sort, a2.key)))

        def __compare_date(self, model, i1, i2):
            a1, a2 = model[i1][0], model[i2][0]
            if (a1 and a2) is None: return cmp(a1, a2)
            elif not a1.sort: return 1
            elif not a2.sort: return -1
            elif not a1.date and a2.date: return 1
            elif not a2.date and a1.date: return -1
            else: return (cmp(a1.date, a2.date) or
                cmp((a1.sort, a1.key), (a2.sort, a2.key)))

    def __init__(self, library, player):
        super(AlbumList, self).__init__(spacing=6)
        self._register_instance()
        if self.__model is None:
            self._init_model(library)
        self.__save = bool(player)

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        self.view = view = AllTreeView()
        view.set_headers_visible(False)
        model_sort = gtk.TreeModelSort(self.__model)
        model_filter = model_sort.filter_new()

        self.__filter = None
        model_filter.set_visible_func(self.__parse_query)

        self.__pending_covers = []
        self.__scan_timeout = None
        view.connect_object('expose-event', self.__update_visibility, view)
        sw.get_vadjustment().connect("value-changed", self.__stop_cover_update)

        render = gtk.CellRendererPixbuf()
        self.__cover_column = column = gtk.TreeViewColumn("covers", render)
        column.set_visible(config.getboolean("browsers", "album_covers"))
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_fixed_width(60)
        render.set_property('height', 56)

        def cell_data_pb(column, cell, model, iter, no_cover):
            album = model[iter][0]
            if album is None: cell.set_property('pixbuf', None)
            elif album.cover: cell.set_property('pixbuf', album.cover)
            else: cell.set_property('pixbuf', no_cover)
        column.set_cell_data_func(render, cell_data_pb, self.__no_cover)
        view.append_column(column)

        render = gtk.CellRendererText()
        self.__column = column = gtk.TreeViewColumn("albums", render)
        render.set_property('ellipsize', pango.ELLIPSIZE_END)
        def cell_data(column, cell, model, iter):
            album = model[iter][0]
            if album is None:
                text = "<b>%s</b>" % _("All Albums")
                text += "\n" + ngettext("%d album", "%d albums",
                        len(model) - 1) % (len(model) - 1)
                cell.markup = text
            else: cell.markup = AlbumList._pattern % model[iter][0]
            cell.set_property('markup', cell.markup)
        column.set_cell_data_func(render, cell_data)
        view.append_column(column)

        view.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        view.set_rules_hint(True)
        view.set_search_equal_func(self.__search_func)
        view.set_search_column(0)
        view.set_model(model_filter)
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw.add(view)

        if player: view.connect('row-activated', self.__play_selection, player)
        self.__sig = view.get_selection().connect('changed',
            self.__selection_changed)

        targets = [("text/x-quodlibet-songs", gtk.TARGET_SAME_APP, 1),
                   ("text/uri-list", 0, 2)]
        view.drag_source_set(
            gtk.gdk.BUTTON1_MASK, targets, gtk.gdk.ACTION_COPY)
        view.connect("drag-data-get", self.__drag_data_get)
        view.connect_object('popup-menu', self.__popup, view, library)

        search = AlbumList.FilterBar(
                self, library, button=False, completion=AlbumTagCompletion())
        search.callback = self.__update_filter
        prefs = gtk.Button()
        prefs.add(gtk.image_new_from_stock(
            gtk.STOCK_PREFERENCES, gtk.ICON_SIZE_MENU))
        prefs.connect('clicked', Preferences)
        search.pack_start(prefs, expand=False)
        self.pack_start(search, expand=False)
        self.pack_start(sw, expand=True)

        hb = gtk.HBox(spacing=6)
        l = gtk.Label(_("Sort _by:"))
        l.set_use_underline(True)
        sc = self.SortCombo(model_sort)
        l.set_mnemonic_widget(sc)
        hb.pack_start(l, expand=False)
        hb.pack_start(sc)
        self.pack_start(hb, expand=False)

        self.show_all()

    def __update_visible_covers(self, view):
        vrange = view.get_visible_range()
        if vrange is None: return

        model_filter = view.get_model()
        model = model_filter.get_model()

        #generate a path list so that cover scanning starts in the middle
        #of the visible area and alternately moves up and down
        preload_count = 35

        start, end = vrange
        start = start[0] - preload_count - 1
        end = end[0] + preload_count

        vlist = range(end, start, -1)
        top = vlist[:len(vlist)/2]
        bottom = vlist[len(vlist)/2:]
        top.reverse()

        vlist_new = []
        for i in vlist:
            if top: vlist_new.append(top.pop())
            if bottom: vlist_new.append(bottom.pop())
        vlist_new = filter(lambda s: s >= 0, vlist_new)

        visible_albums = []
        for path in vlist_new:
            model_path = model_filter.convert_path_to_child_path(path)
            try:
                row = model[model_path]
            except TypeError:
                pass
            else:
                album = row[0]
                if album is not None and not album.scanned:
                    visible_albums.append([model, model_path])

        if not self.__pending_covers and visible_albums:
            copool.add(self.__scan_covers)
        self.__pending_covers = visible_albums

    def __scan_covers(self):
        while self.__pending_covers:
            model, path = self.__pending_covers.pop()
            row = model[path]
            album = row[0]
            album.scan_cover()
            self._refresh_albums([album])
            yield True

    def __stop_cover_update(self, *args):
        self.__pending_covers = []

    def __update_visibility(self, view, *args):
        if not self.__cover_column.get_visible():
            return

        if self.__scan_timeout:
            gobject.source_remove(self.__scan_timeout)
            self.__scan_timeout = None

        self.__scan_timeout = gobject.timeout_add(
            50, self.__update_visible_covers, view)

    def __update_filter(self, text):
        #This could be called after the browsers is already closed
        if not self.view.get_selection(): return
        model = self.view.get_model()
        if Query.is_parsable(text):
            if not text:
                self.__filter = None
            else:
                self.__filter = Query(text, star=["people", "album"]).search
        self.__inhibit()
        model.refilter()
        self.__uninhibit()

    def __parse_query(self, model, iter):
        if self.__filter is None: return True
        elif model[iter][0] is None: return True
        else: return self.__filter(model[iter][0])

    def __search_func(self, model, column, key, iter):
        album = model[iter][0]
        if album is None: return True
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
        songs = self.__get_selected_songs(view.get_selection())
        menu = SongsMenu(library, songs, parent=self)

        button = gtk.ImageMenuItem(gtk.STOCK_REFRESH)
        button.connect('activate', self.__refresh_album, view)
        menu.prepend(gtk.SeparatorMenuItem())
        menu.prepend(button)
        menu.show_all()
        return view.popup_menu(menu, 0, gtk.get_current_event_time())

    def __refresh_album(self, menuitem, view):
        selection = view.get_selection()
        model, paths = selection.get_selected_rows()
        albums = [model[path][0] for path in paths]
        if None in albums:
            albums = [row[0] for row in model if row[0]]
        for album in albums:
            album.scanned = False
            album.scan_cover()
        self._refresh_albums(albums)

    def __get_selected_albums(self, selection):
        if not selection:
            return []
        model, rows = selection.get_selected_rows()
        if not model or not rows: return set([])
        albums = [model[row][0] for row in rows]
        if None in albums: return None
        else: return albums

    def __get_selected_songs(self, selection, sort=True):
        if not selection:
            return []
        model, rows = selection.get_selected_rows()
        if not model or not rows: return []
        albums = [model[row][0] for row in rows]
        if None in albums:
            albums = [row[0] for row in model if row[0]]
        # Sort first by how the albums appear in the model itself,
        # then within the album using the default order.
        songs = []
        if sort:
            for album in albums:
                songs.extend(sorted(album.songs))
        else:
            for album in albums:
                songs.extend(album.songs)
        return songs

    def __drag_data_get(self, view, ctx, sel, tid, etime):
        songs = self.__get_selected_songs(view.get_selection())
        if tid == 1:
            filenames = [song("~filename") for song in songs]
            sel.set("text/x-quodlibet-songs", 8, "\x00".join(filenames))
        else: sel.set_uris([song("~uri") for song in songs])

    def __play_selection(self, view, indices, col, player):
        player.reset()

    def filter(self, key, values):
        assert(key == "album")
        if not values: values = [""]
        view = self.view
        selection = view.get_selection()
        selection.unselect_all()
        model = view.get_model()
        first = None
        for row in model:
            if row[0] is not None and row[0].title in values:
                selection.select_path(row.path)
                if first is None:
                    view.set_cursor(row.path)
                    first = row.path[0]
        if first:
            view.scroll_to_cell(first, use_align=True, row_align=0.5)

    def unfilter(self):
        selection = self.view.get_selection()
        selection.unselect_all()
        selection.select_path((0,))

    def activate(self):
        self.view.get_selection().emit('changed')

    def can_filter(self, key):
        return (key == "album")

    def list(self, key):
        assert (key == "album")
        model = self.view.get_model()
        return [row[0].title for row in model if row[0]]

    def __inhibit(self):
        self.view.get_selection().handler_block(self.__sig)

    def __uninhibit(self):
        self.view.get_selection().handler_unblock(self.__sig)

    def restore(self):
        albums = config.get("browsers", "albums").split("\n")
        view = self.view
        selection = view.get_selection()
        # FIXME: If albums is "" then it could be either all albums or
        # no albums. If it's "" and some other stuff, assume no albums,
        # otherwise all albums.
        self.__inhibit()
        selection.unselect_all()
        if albums == [""]:  selection.select_path((0,))
        else:
            model = selection.get_tree_view().get_model()
            first = None
            for row in model:
                if row[0] is not None and row[0].title in albums:
                    selection.select_path(row.path)
                    first = first or row.path

            if first:
                view.scroll_to_cell(first[0], use_align=True, row_align=0.5)
        self.__uninhibit()

    def scroll(self, song):
        view = self.view
        model = view.get_model()
        album_key = song.album_key
        for row in model:
            if row[0] is not None and row[0].key == album_key:
                view.scroll_to_cell(row.path[0], use_align=True, row_align=0.5)
                sel = view.get_selection()
                sel.unselect_all()
                sel.select_path(row.path[0])
                break

    def __selection_changed(self, selection):
        # Without this delay, GTK+ seems to sometimes call this function
        # before model elements are totally filled in, leading to errors
        # like "TypeError: unknown type (null)".
        gobject.idle_add(self.__update_songs, selection.get_tree_view())

    def __update_songs(self, view):
        selection = view.get_selection()
        songs = self.__get_selected_songs(selection, False)
        albums = self.__get_selected_albums(selection)
        if not songs:
            return
        self.emit('songs-selected', songs, None)
        if self.__save:
            if albums is None:
                config.set("browsers", "albums", "")
            else:
                confval = "\n".join([a.title for a in albums])
                # Since ConfigParser strips a trailing \n...
                if confval and confval[-1] == "\n":
                    confval = "\n" + confval[:-1]
                config.set("browsers", "albums", confval)

browsers = [AlbumList]
