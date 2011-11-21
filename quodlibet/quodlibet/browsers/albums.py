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
from quodlibet.parse import Query, XMLFromPattern
from quodlibet.qltk.ccb import ConfigCheckButton
from quodlibet.qltk.completion import EntryWordCompletion
from quodlibet.qltk.songsmenu import SongsMenu
from quodlibet.qltk.textedit import PatternEditBox
from quodlibet.qltk.views import AllTreeView
from quodlibet.qltk.x import MenuItem
from quodlibet.qltk.searchbar import SearchBarBox
from quodlibet.util import copool, gobject_weak, thumbnails
from quodlibet.util.library import background_filter

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
        gobject_weak(cb.connect, 'toggled', lambda s: AlbumList.toggle_covers())
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
        gobject_weak(edit.apply.connect, 'clicked', self.__set_pattern, edit)
        gobject_weak(edit.buffer.connect_object, 'changed',
            self.__preview_pattern, edit, label, parent=edit)

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
    __last_render = None
    __last_render_pb = None

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

        theme = gtk.icon_theme_get_default()
        try:
            klass.__no_cover = theme.load_icon(
                "quodlibet-missing-cover", 48, 0)
        except gobject.GError: pass
        else:
            klass.__no_cover = thumbnails.scale(
                klass.__no_cover, (48, 48))

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
        klass.__sigs = [
            library.albums.connect("added", klass._add_albums, model),
            library.albums.connect("removed", klass._remove_albums, model),
            library.albums.connect("changed", klass._change_albums, model)]
        model.append(row=[None])
        for album in library.albums.itervalues():
            model.append(row=[album])

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
                if not removed_albums: break

    @classmethod
    def _change_albums(klass, library, changed, model):
        """Trigger a row redraw for each album that changed"""
        changed_albums = changed.copy()
        for row in model:
            if row[0] and row[0] in changed_albums:
                changed_albums.remove(row[0])
                model.row_changed(row.path, row.iter)
                if not changed_albums: break

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

            gobject_weak(self.connect_object, 'changed',
                self.__set_cmp_func, model)

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
            elif not a1.title: return 1
            elif not a2.title: return -1
            elif not a1.sort: return 1
            elif not a2.sort: return -1
            else: return cmp((a1.sort, a1.key), (a2.sort, a2.key))

        def __compare_artist(self, model, i1, i2):
            a1, a2 = model[i1][0], model[i2][0]
            if (a1 and a2) is None: return cmp(a1, a2)
            elif not a1.title: return 1
            elif not a2.title: return -1
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
            elif not a1.title: return 1
            elif not a2.title: return -1
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

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        self.view = view = AllTreeView()
        view.set_headers_visible(False)
        model_sort = gtk.TreeModelSort(self.__model)
        model_filter = model_sort.filter_new()

        self.__bg_filter = background_filter()
        self.__filter = None
        model_filter.set_visible_func(self.__parse_query)

        self.__pending_covers = []
        self.__scan_timeout = None
        gobject_weak(view.connect_object, 'expose-event',
            self.__update_visibility, view)

        gobject_weak(sw.get_vadjustment().connect, "value-changed",
            self.__stop_cover_update)

        render = gtk.CellRendererPixbuf()
        self.__cover_column = column = gtk.TreeViewColumn("covers", render)
        column.set_visible(config.getboolean("browsers", "album_covers"))
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_fixed_width(60)
        render.set_property('height', 56)

        def cell_data_pb(column, cell, model, iter, no_cover):
            album = model[iter][0]
            if album is None: pixbuf = None
            elif album.cover: pixbuf = album.cover
            else: pixbuf = no_cover
            if self.__last_render_pb == pixbuf: return
            self.__last_render_pb = pixbuf
            cell.set_property('pixbuf', pixbuf)

        column.set_cell_data_func(render, cell_data_pb, self.__no_cover)
        view.append_column(column)

        render = gtk.CellRendererText()
        column = gtk.TreeViewColumn("albums", render)
        render.set_property('ellipsize', pango.ELLIPSIZE_END)

        def cell_data(column, cell, model, iter):
            album = model[iter][0]
            if album is None:
                text = "<b>%s</b>" % _("All Albums")
                text += "\n" + ngettext("%d album", "%d albums",
                        len(model) - 1) % (len(model) - 1)
                markup = text
            else:
                markup = AlbumList._pattern % album

            if self.__last_render == markup: return
            self.__last_render = markup
            cell.markup = markup
            cell.set_property('markup', markup)

        column.set_cell_data_func(render, cell_data)
        view.append_column(column)

        view.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        view.set_rules_hint(True)
        view.set_search_equal_func(self.__search_func)
        view.set_search_column(0)
        view.set_model(model_filter)
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw.add(view)

        if player:
            gobject_weak(view.connect, 'row-activated',
                self.__play_selection, player)

        self.__sig = gobject_weak(view.get_selection().connect, 'changed',
            util.DeferredSignal(self.__update_songs), parent=view)

        targets = [("text/x-quodlibet-songs", gtk.TARGET_SAME_APP, 1),
                   ("text/uri-list", 0, 2)]
        view.drag_source_set(
            gtk.gdk.BUTTON1_MASK, targets, gtk.gdk.ACTION_COPY)
        gobject_weak(view.connect, "drag-data-get", self.__drag_data_get)
        gobject_weak(view.connect_object, 'popup-menu',
            self.__popup, view, library)

        self.accelerators = gtk.AccelGroup()
        search = SearchBarBox(button=False, completion=AlbumTagCompletion(),
                              accel_group=self.accelerators)
        search.connect('query-changed', self.__update_filter)
        search.connect_object('focus-out', lambda w: w.grab_focus(), view)
        self.__search = search

        prefs = gtk.Button()
        prefs.add(gtk.image_new_from_stock(
            gtk.STOCK_PREFERENCES, gtk.ICON_SIZE_MENU))
        gobject_weak(prefs.connect, 'clicked', Preferences)
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

        self.connect("destroy", self.__destroy)

        self.show_all()

    def __destroy(self, browser):
        copool.remove(self.__scan_covers)

        # https://bugzilla.gnome.org/show_bug.cgi?id=624112
        # filter model keeps its filter function reference.
        # at least try to get rid of as much data as possible.
        self.__inhibit()
        model = self.view.get_model()
        self.view.set_model(None)
        model.clear_cache()
        model = model.get_model()
        model.clear_cache()
        self.__dict__.clear()

        klass = type(browser)
        if not klass.instances():
            klass._destroy_model()

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
            try:
                row = model[path]
            # row could have gone away by now
            except IndexError: pass
            else:
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

    def __update_filter(self, entry, text, restore=False):
        #This could be called after the browsers is already closed
        if not self.view.get_selection(): return
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
        if not restore:
            self.view.scroll_to_point(0, 0)

        # don't filter on restore if there is nothing to filter
        if not restore or self.__filter or self.__bg_filter:
            model.refilter()

        self.__uninhibit()

    def __parse_query(self, model, iter):
        # leaked filter models try to refilter on model changes
        if not self.__dict__: return

        f, b = self.__filter, self.__bg_filter
        if f is None and b is None: return True
        elif model[iter][0] is None: return True
        elif b is None: return f(model[iter][0])
        elif f is None: return b(model[iter][0])
        else: return b(model[iter][0]) and f(model[iter][0])

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
        selection = view.get_selection()
        albums = self.__get_selected_albums(selection)
        songs = self.__get_songs_from_albums(albums)
        menu = SongsMenu(library, songs, parent=self)

        if self.__cover_column.get_visible():
            num = len(albums)
            button = MenuItem(
                ngettext("Reload album _cover", "Reload album _covers", num),
                gtk.STOCK_REFRESH)
            gobject_weak(button.connect, 'activate',
                self.__refresh_album, view)
            menu.prepend(gtk.SeparatorMenuItem())
            menu.prepend(button)

        menu.show_all()
        return view.popup_menu(menu, 0, gtk.get_current_event_time())

    def __refresh_album(self, menuitem, view):
        selection = view.get_selection()
        albums = self.__get_selected_albums(selection)
        for album in albums:
            album.scanned = False
            album.scan_cover()
        self._refresh_albums(albums)

    def __get_selected_albums(self, selection):
        if not selection:
            return []
        model, rows = selection.get_selected_rows()
        if not model or not rows: return []
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

    def __get_selected_songs(self, selection, sort=True):
        albums = self.__get_selected_albums(selection)
        return self.__get_songs_from_albums(albums, sort)

    def __drag_data_get(self, view, ctx, sel, tid, etime):
        songs = self.__get_selected_songs(view.get_selection())
        if tid == 1:
            filenames = [song("~filename") for song in songs]
            sel.set("text/x-quodlibet-songs", 8, "\x00".join(filenames))
        else: sel.set_uris([song("~uri") for song in songs])

    def __play_selection(self, view, indices, col, player):
        player.reset()

    def active_filter(self, song):
        key = song.album_key

        selection = self.view.get_selection()
        if not selection:
            return False

        model, rows = selection.get_selected_rows()
        if not model or not rows:
            return False

        if rows and model[rows[0]][0] is None:
            return True

        for album in [model[row][0] for row in rows]:
            if key == album.key:
                return True

        return False

    def filter(self, key, values):
        assert(key == "album")
        if not values: values = [""]
        view = self.view
        self.__inhibit()
        selection = view.get_selection()
        model = view.get_model()
        first = True
        for row in model:
            if row[0] is not None and row[0].title in values:
                if first:
                    view.scroll_to_cell(row.path[0],
                        use_align=True, row_align=0.5)
                    view.set_cursor(row.path)
                    first = False
                else:
                    selection.select_path(row.path)
        self.__uninhibit()
        if not first:
            selection.emit('changed')

    def unfilter(self):
        self.view.set_cursor((0,))

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
        text = config.get("browsers", "query_text").decode("utf-8")
        entry = self.__search
        entry.set_text(text)
        self.__update_filter(entry, text, restore=True)

        albums = config.get("browsers", "albums").split("\n")
        view = self.view
        selection = view.get_selection()
        # FIXME: If albums is "" then it could be either all albums or
        # no albums. If it's "" and some other stuff, assume no albums,
        # otherwise all albums.
        self.__inhibit()
        if albums == [""]:
            selection.unselect_all()
            selection.select_path((0,))
        else:
            model = selection.get_tree_view().get_model()
            first = True
            for row in model:
                if row[0] is not None and row[0].title in albums:
                    if first:
                        view.scroll_to_cell(row.path, use_align=True,
                                            row_align=0.5)
                        view.set_cursor(row.path)
                        first = False
                    else:
                        selection.select_path(row.path)
        self.__uninhibit()

    def scroll(self, song):
        view = self.view
        model = view.get_model()
        album_key = song.album_key
        for row in model:
            if row[0] is not None and row[0].key == album_key:
                view.scroll_to_cell(row.path[0], use_align=True, row_align=0.5)
                view.set_cursor(row.path)
                break

    def __get_config_string(self, selection):
        if not selection: return ""
        model, rows = selection.get_selected_rows()
        if not model or not rows: return ""

        # All is selected
        if rows and model[rows[0]][0] is None: return ""

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
        if not self.__dict__: return
        songs = self.__get_selected_songs(selection, False)
        self.emit('songs-selected', songs, None)

browsers = [AlbumList]
