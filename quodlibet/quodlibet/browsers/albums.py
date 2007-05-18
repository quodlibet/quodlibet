# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os

import gobject
import gtk
import pango

from quodlibet import config
from quodlibet import const
from quodlibet import qltk
from quodlibet import stock
from quodlibet import util

from quodlibet.browsers._base import Browser
from quodlibet.formats import PEOPLE
from quodlibet.parse import Query, XMLFromPattern
from quodlibet.qltk.ccb import ConfigCheckButton
from quodlibet.qltk.completion import EntryWordCompletion
from quodlibet.qltk.entry import ValidatingEntry
from quodlibet.qltk.songsmenu import SongsMenu
from quodlibet.qltk.textedit import PatternEditBox
from quodlibet.qltk.views import AllTreeView
from quodlibet.util import copool, tag

ELPOEP = list(PEOPLE); ELPOEP.reverse()
EMPTY = _("Songs not in an album")
PATTERN = r"""\<b\><title|\<i\><title>\</i\>|%s>\</b\><date| (<date>)>
\<small\><~discs|<~discs> - ><~tracks> - <~long-length>\</small\>
<people>""" % EMPTY

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

class Preferences(qltk.Window):
    def __init__(self):
        super(Preferences, self).__init__()
        self.set_border_width(12)
        self.set_title(_("Album List Preferences") + " - Quod Libet")
        self.add(gtk.VBox(spacing=6))
        self.set_default_size(300, 200)
        self.connect_object('delete-event', Preferences.__delete_event, self)

        cb = ConfigCheckButton(
            _("Show album _covers"), "browsers", "album_covers")
        cb.set_active(config.getboolean("browsers", "album_covers"))
        cb.connect('toggled', lambda s: AlbumList.toggle_covers())
        self.child.pack_start(cb, expand=False)

        vbox = gtk.VBox(spacing=6)
        label = gtk.Label()
        label.set_alignment(0.0, 0.5)
        edit = PatternEditBox(PATTERN)
        edit.text = AlbumList._Album._pattern_text
        edit.apply.connect('clicked', self.__set_pattern, edit)
        edit.buffer.connect_object(
            'changed', self.__preview_pattern, edit, label)
        vbox.pack_start(label, expand=False)
        vbox.pack_start(edit)
        self.__preview_pattern(edit, label)
        f = qltk.Frame(_("Album Display"), child=vbox)
        self.child.pack_start(f)

        self.child.show_all()

    def __delete_event(self, event):
        self.hide()
        return True

    def __set_pattern(self, apply, edit):
        AlbumList.refresh_pattern(edit.text)

    def __preview_pattern(self, edit, label):
        album = AlbumList._Album(
            util.tag("album"), util.tag("labelid"),
            util.tag("musicbrainz_albumid"))
        album.date = "2004-10-31"
        album.length = 6319
        album.discs = 2
        album.tracks = 5
        album.people = [tag("artist"), tag("performer"), tag("arranger")]
        album.genre = tag("genre")
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

    name = _("Album List")
    accelerated_name = _("_Album List")
    priority = 4

    @classmethod
    def init(klass, library):
        pattern_fn = os.path.join(const.USERDIR, "album_pattern")
        try:
            klass._Album._pattern_text = file(pattern_fn).read().rstrip()
        except EnvironmentError: pass
        else:
            klass._Album._pattern = XMLFromPattern(klass._Album._pattern_text)
        try:
            klass._Album.cover = gtk.gdk.pixbuf_new_from_file_at_size(
                stock.NO_ALBUM, 48, 48)
        except RuntimeError:
            klass._Album.cover = None

    @classmethod
    def toggle_covers(klass):
        on = config.getboolean("browsers", "album_covers")
        for albumlist in klass.instances():
            albumlist.__cover_column.set_visible(on)

    @classmethod
    def refresh_pattern(klass, pattern_text):
        if pattern_text == klass._Album._pattern_text: return
        klass._Album._pattern_text = pattern_text
        klass._Album._pattern = XMLFromPattern(pattern_text)
        for album in [row[0] for row in klass.__model if row[0] is not None]:
            album.finalize(cover=False)
        pattern_fn = os.path.join(const.USERDIR, "album_pattern")
        f = file(pattern_fn, "w")
        f.write(pattern_text  + "\n")
        f.close()

    @classmethod
    def _init_model(klass, library):
        klass.__model = model = klass._AlbumStore(object)
        library.connect('removed', klass.__remove_songs, model)
        library.connect('changed', klass.__changed_songs, model)
        library.connect('added', klass.__add_songs, model)
        klass.__add_songs(library, library.values(), model)
        model.append(row=[None])

    @classmethod
    def __changed_songs(klass, library, changed, model):
        to_update = klass.__remove_songs(library, changed, model, False)
        to_update.update(klass.__add_songs(library, changed, model, False))
        klass.__update(to_update, model)

    @classmethod
    def __update(klass, changed, model):
        to_change = []
        to_remove = []
        for row in model:
            album = row[0]
            if album is not None and album.key in changed:
                if album.songs:
                    to_change.append((row.path, row.iter))
                    album.finalize()
                else:
                    to_remove.append(row.iter)
                    album._model = album._iter = None
        if to_change: map(model.row_changed, *zip(*to_change))
        if to_remove: map(model.remove, to_remove)

    @classmethod
    def __remove_songs(klass, library, removed, model, update=True):
        changed = set()
        for row in model:
            album = row[0]
            if album is not None and True in map(album.remove, removed):
                changed.add(album.key)
        if update: klass.__update(changed, model)
        else: return changed

    @classmethod
    def __add_songs(klass, library, added, model, update=True):
        albums = model.get_albums()
        changed = set() # Keys of changed albums
        new = [] # Added album instances
        for song in added:
            labelid = song.get("labelid", "")
            mbid = song.get("musicbrainz_albumid", "")
            key = song.album_key
            if key not in albums:
                new_album = klass._Album(song("album"), labelid, mbid)
                albums[key] = new_album
                new.append(new_album)
            albums[key].songs.add(song)
            changed.add(key)
        for album in new:
            model.append(row=[album])
        if update: klass.__update(changed, model)
        else: return changed

    # Something like an AudioFile, but for a whole album.
    class _Album(object):
        __pending_covers = []

        _pattern_text = PATTERN
        _pattern = XMLFromPattern(PATTERN)

        length = 0
        discs = 1
        tracks = 0
        date = ""
        markup = ""

        def __init__(self, title, labelid, mbid):
            self.people = []
            self.songs = set()
            self.title = title
            # The key uniquely identifies the album; this way, albums
            # with different MBIDs or different label IDs but the same
            # title are different, and albums with different MBIDs
            # but the same label ID are the same (since MB uses separate
            # MBIDs for each disc).
            self.key = (title, labelid or mbid)

        def get(self, key, default="", connector=u" - "):
            if "~" in key[1:]:
                return connector.join(map(self.get, util.tagsplit(key)))
            elif key == "~#length": return self.length
            elif key == "~#tracks": return self.tracks
            elif key == "~#discs": return self.discs
            elif key == "~length": return util.format_time(self.length)
            elif key == "date": return self.date
            elif key == "~long-length":
                return util.format_time_long(self.length)
            elif key in ["cover", "~cover"]: return (self.cover and "y") or ""
            elif key in ["title", "album"]: return self.title
            elif key == "people":
                return "\n".join(self.people)
            elif key.startswith("~#") and key[-4:-3] != ":": key += ":avg"
            elif key == "~tracks":
                return ngettext(
                    "%d track", "%d tracks", self.tracks) % self.tracks
            elif key == "~discs":
                if self.discs > 1:
                    return ngettext(
                        "%d disc", "%d discs", self.discs) % self.discs
                else: return default

            if key.startswith("~#") and key[-4:-3] == ":":
                # Using key:<func> runs the resulting list of values
                # through the function before returning it.
                func = key[-3:]
                key = key[:-4]
                func = {"max": max, "min": min, "sum": sum,
                        "avg": lambda s: float(sum(s)) / len(s)}.get(func)
                if func: return func([song(key, 0) for song in self.songs])

            # Otherwise, if the tag isn't one provided by the album
            # object, look in songs for it.
            values = set()
            for song in self.songs: values.update(song.list(key))
            value = u"\n".join(list(values))
            return value or default

        __call__ = get
        def comma(self, *args):
            return self.get(*args).replace("\n", ", ")

        # All songs added, cache info.
        def finalize(self, cover=True):
            self.tracks = len(self.songs)
            self.length = 0
            people = {}
            for song in self.songs:
                # Rank people by "relevance" -- artists before composers
                # before performers, then by number of appearances.
                for w, key in enumerate(ELPOEP):
                    for person in song.list(key):
                        people[person] = people.get(person, 0) - 1000 ** w

                self.discs = max(self.discs, song("~#disc", 0))
                self.length += song.get("~#length", 0)

            self.people = sorted(people.keys(), key=people.__getitem__)[:100]

            if not self.title:
                self.date = ""
                self.discs = 1
            else: self.date = song.comma("date")

            self.markup = self._pattern % self
            self._model[self._iter][0] = self

        def remove(self, song):
            try: self.songs.remove(song)
            except KeyError: return False
            else: return True

    # An auto-searching entry; it wraps is a TreeModelFilter whose parent
    # is the album list.
    class FilterEntry(ValidatingEntry):
        def __init__(self, model):
            ValidatingEntry.__init__(self, Query.is_valid_color)
            self.connect_object('changed', self.__filter_changed, model)
            self.set_completion(AlbumTagCompletion())
            self.__refill_id = None
            self.__filter = None
            self.inhibit = False
            model.set_visible_func(self.__parse)

        def __parse(self, model, iter):
            if self.__filter is None: return True
            elif model[iter][0] is None: return True
            else: return self.__filter(model[iter][0])

        def __filter_changed(self, model):
            if self.__refill_id is not None:
                gobject.source_remove(self.__refill_id)
                self.__refill_id = None
            text = self.get_text().decode('utf-8')
            if Query.is_parsable(text):
                if not text: self.__filter = None
                else:
                    self.__filter = Query(
                        text, star=["people", "album"]).search
                self.__refill_id = gobject.timeout_add(
                    500, self.__refilter, model)

        def __refilter(self, model):
            self.inhibit = True
            model.refilter()
            self.inhibit = False

    # Sorting, either by people or album title. It wraps a TreeModelSort
    # whose parent is the album list.
    class SortCombo(gtk.ComboBox):
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

            for text in [
                _("Sort by title"), _("Sort by artist"), _("Sort by date")
                ]: cbmodel.append(row=[text])

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
            elif not a1.title: return 1
            elif not a2.title: return -1
            else: return cmp(a1.key, a2.key)

        def __compare_artist(self, model, i1, i2):
            a1, a2 = model[i1][0], model[i2][0]
            if (a1 and a2) is None: return cmp(a1, a2)
            elif not a1.title: return 1
            elif not a2.title: return -1
            elif not a1.people and a2.people: return 1
            elif not a2.people and a1.people: return -1
            else: return (cmp(a1.people and a1.people[0],
                              a2.people and a2.people[0]) or
                          cmp(a1.date or "ZZZZ", a2.date or "ZZZZ") or
                          cmp(a1.key, a2.key))

        def __compare_date(self, model, i1, i2):
            a1, a2 = model[i1][0], model[i2][0]
            if (a1 and a2) is None: return cmp(a1, a2)
            elif not a1.title: return 1
            elif not a2.title: return -1
            elif not a1.date and a2.date: return 1
            elif not a2.date and a1.date: return -1
            else: return (cmp(a1.date, a2.date) or cmp(a1.key, a2.key))

    class _AlbumStore(gtk.ListStore):
        __gsignals__ = { "row-changed": "override" }

        def __init__(self, *args, **kwargs):
            super(AlbumList._AlbumStore, self).__init__(*args, **kwargs)
            self.__pending_covers = []

        def do_row_changed(self, path, iter):
            album = self[iter][0]
            if album is None:
                return
            album._model = self
            album._iter = iter
            if album.title and album.cover is type(album).cover:
                if not self.__pending_covers:
                    copool.add(self.__scan_covers)
                self.__pending_covers.append(album)

        def __scan_covers(self):
            while self.__pending_covers:
                album = self.__pending_covers.pop()
                if album._iter is None or album.cover is not type(album).cover:
                    continue
                song = list(album.songs)[0]
                cover = song.find_cover()
                if cover is not None:
                    try:
                        cover = gtk.gdk.pixbuf_new_from_file_at_size(
                            cover.name, 48, 48)
                    except StandardError:
                        continue
                    else:
                        # add a black outline
                        w, h = cover.get_width(), cover.get_height()
                        newcover = gtk.gdk.Pixbuf(
                            gtk.gdk.COLORSPACE_RGB, True, 8, w + 2, h + 2)
                        newcover.fill(0x000000ff)
                        cover.copy_area(0, 0, w, h, newcover, 1, 1)
                        album.cover = newcover
                        self[album._iter][0] = album
                yield True

        def get_albums(self):
            albums = [row[0] for row in self]
            try: albums.remove(None)
            except ValueError: pass
            return dict([(a.key, a) for a in albums])

    def __init__(self, library, player):
        super(AlbumList, self).__init__(spacing=6)
        self._register_instance()
        if self.__model is None: AlbumList._init_model(library)
        self.__save = bool(player)

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        view = AllTreeView()
        view.set_headers_visible(False)
        model_sort = gtk.TreeModelSort(self.__model)
        model_filter = model_sort.filter_new()

        render = gtk.CellRendererPixbuf()
        self.__cover_column = column = gtk.TreeViewColumn("covers", render)
        column.set_visible(config.getboolean("browsers", "album_covers"))
        column.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
        render.set_property('xpad', 2)
        render.set_property('ypad', 2)
        render.set_property('width', 56)
        render.set_property('height', 56)

        def cell_data_pb(column, cell, model, iter):
            album = model[iter][0]
            if album is None: cell.set_property('pixbuf', None)
            elif album.cover: cell.set_property('pixbuf', album.cover)
            else: cell.set_property('pixbuf', None)
        column.set_cell_data_func(render, cell_data_pb)
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
                cell.markup = text
            else: cell.markup = model[iter][0].markup
            cell.set_property('markup', cell.markup)
        column.set_cell_data_func(render, cell_data)
        view.append_column(column)

        view.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        view.set_rules_hint(True)
        view.set_search_equal_func(self.__search_func)
        view.set_search_column(0)
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw.add(view)
        e = self.FilterEntry(model_filter)
        hb2 = gtk.HBox()
        hb2.pack_start(e)
        hb2.pack_start(qltk.ClearButton(e), expand=False)

        if player: view.connect('row-activated', self.__play_selection, player)
        view.get_selection().connect('changed', self.__selection_changed, e)

        targets = [("text/x-quodlibet-songs", gtk.TARGET_SAME_APP, 1),
                   ("text/uri-list", 0, 2)]
        view.drag_source_set(
            gtk.gdk.BUTTON1_MASK, targets, gtk.gdk.ACTION_COPY)
        view.connect("drag-data-get", self.__drag_data_get)
        view.connect_object('popup-menu', self.__popup, view, library)

        hb = gtk.HBox(spacing=6)
        hb.pack_start(self.SortCombo(model_sort), expand=False)
        hb.pack_start(hb2)
        prefs = gtk.Button()
        prefs.add(
            gtk.image_new_from_stock(gtk.STOCK_PREFERENCES, gtk.ICON_SIZE_MENU))
        prefs.connect('clicked', self.__preferences)
        hb.pack_start(prefs, expand=False)
        self.pack_start(hb, expand=False)
        self.pack_start(sw, expand=True)
        view.set_model(model_filter)
        self.show_all()

    def __search_func(self, model, column, key, iter):
        try: value = model[iter][0].title
        except AttributeError: return True
        else:
            key = key.decode('utf-8')
            return not (value.startswith(key) or value.lower().startswith(key))
        
    def __popup(self, view, library):
        songs = self.__get_selected_songs(view.get_selection())
        menu = SongsMenu(library, songs)

        button = gtk.ImageMenuItem(gtk.STOCK_REFRESH)
        button.connect('activate', self.__refresh_album, view.get_selection())
        menu.prepend(gtk.SeparatorMenuItem())
        menu.prepend(button)
        menu.show_all()
        return view.popup_menu(menu, 0, gtk.get_current_event_time())

    def __refresh_album(self, menuitem, selection):
        model, rows = selection.get_selected_rows()
        albums = [model[row][0] for row in rows]
        if None in albums:
            albums = [model[row][0] for row in model]
        for album in albums:
            album.cover = type(album).cover
            album.finalize()

    def __get_selected_albums(self, selection):
        model, rows = selection.get_selected_rows()
        if not model or not rows: return set([])
        albums = [model[row][0] for row in rows]
        if None in albums: return None
        else: return albums

    def __get_selected_songs(self, selection):
        model, rows = selection.get_selected_rows()
        if not model or not rows: return []
        albums = [model[row][0] for row in rows]
        if None in albums:
            albums = [row[0] for row in model if row[0]]
        # Sort first by how the albums appear in the model itself,
        # then within the album using the default order.
        songs = []
        for album in albums:
            songs.extend(sorted(album.songs))
        return songs

    def __drag_data_get(self, view, ctx, sel, tid, etime):
        songs = self.__get_selected_songs(view.get_selection())
        if tid == 1:
            filenames = [song("~filename") for song in songs]
            sel.set("text/x-quodlibet-songs", 8, "\x00".join(filenames))
        else: sel.set_uris([song("~uri") for song in songs])
        
    def __play_selection(self, view, indices, col, player):
        player.reset()

    def __preferences(self, button):
        try: prefs = AlbumList.__prefs_win
        except AttributeError: prefs = AlbumList.__prefs_win = Preferences()
        win = qltk.get_top_parent(self)
        top, left = win.get_position()
        w, h = win.get_size()
        dw, dh = prefs.get_size()
        prefs.move((left + w // 2) - dw // 2, (top + h // 2) - dh // 2)
        prefs.present()

    def filter(self, key, values):
        assert(key == "album")
        if not values: values = [""]
        view = self.get_children()[1].child
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
        view = self.get_children()[1].child
        selection = view.get_selection()
        selection.unselect_all()
        selection.select_path((0,))

    def activate(self):
        self.get_children()[1].child.get_selection().emit('changed')

    def can_filter(self, key):
        return (key == "album")

    def list(self, key):
        assert (key == "album")
        view = self.get_children()[1].child
        model = view.get_model()
        return [row[0].title for row in model if row[0]]

    def restore(self):
        albums = config.get("browsers", "albums").split("\n")
        view = self.get_children()[1].child
        selection = view.get_selection()
        # FIXME: If albums is "" then it could be either all albums or
        # no albums. If it's "" and some other stuff, assume no albums,
        # otherwise all albums.
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

    def scroll(self, song):
        view = self.get_children()[1].child
        model = view.get_model()
        values = song.list("album")
        album_key = song.album_key
        for row in model:
            if row[0] is not None and row[0].key == album_key:
                view.scroll_to_cell(row.path[0], use_align=True, row_align=0.5)
                break

    def __selection_changed(self, selection, sort):
        if sort.inhibit: return
        songs = self.__get_selected_songs(selection)
        albums = self.__get_selected_albums(selection)
        if not songs: return
        self.emit('songs-selected', songs, None)
        if self.__save:
            if albums is None: config.set("browsers", "albums", "")
            else:
                confval = "\n".join([a.title for a in albums])
                # Since ConfigParser strips a trailing \n...
                if confval and confval[-1] == "\n":
                    confval = "\n" + confval[:-1]
                config.set("browsers", "albums", confval)

browsers = [AlbumList]
