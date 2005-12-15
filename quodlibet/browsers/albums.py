# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import sys
import gobject, gtk, pango
import config
import qltk
import util
import stock
from qltk.completion import EntryWordCompletion
from qltk.views import HintedTreeView
from qltk.entry import ValidatingEntry
from parse import Query
from formats._audio import PEOPLE
ELPOEP = list(PEOPLE); ELPOEP.reverse()

if sys.version_info < (2, 4): from sets import Set as set
from library import library
from browsers._base import Browser
from qltk.properties import SongProperties
from qltk.information import Information

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

class AlbumList(Browser, gtk.VBox):
    expand = qltk.RHPaned
    __gsignals__ = Browser.__gsignals__
    __model = None

    def _init_model(klass, watcher):
        klass.__model = model = klass._AlbumStore(object)
        watcher.connect('removed', klass.__remove_songs, model)
        watcher.connect('changed', klass.__changed_songs, model)
        watcher.connect('added', klass.__add_songs, model)
        klass.__add_songs(watcher, library.values(), model)
        model.append(row=[None])
    _init_model = classmethod(_init_model)

    def __changed_songs(klass, watcher, changed, model):
        changed = filter(lambda x: x.get("~filename") in library, changed)
        if not changed: return
        klass.__remove_songs(watcher, changed, model)
        klass.__add_songs(watcher, changed, model)
    __changed_songs = classmethod(__changed_songs)

    def __update(klass, changed, model):
        to_change = []
        to_remove = []
        def update(model, path, iter):
            album = model[iter][0]
            if album is not None and album.title in changed:
                if album.songs:
                    to_change.append((path, iter))
                    album.finalize()
                else: to_remove.append(iter)
        model.foreach(update)
        if to_change: map(model.row_changed, *zip(*to_change))
        if to_remove: map(model.remove, to_remove)
    __update = classmethod(__update)

    def __remove_songs(klass, watcher, removed, model):
        albums = model.get_albums()
        changed = set()
        for album in albums.itervalues():
            if True in map(album.remove, removed): changed.add(album.title)
        klass.__update(changed, model)
    __remove_songs = classmethod(__remove_songs)

    def __add_songs(klass, watcher, added, model):
        albums = model.get_albums()
        changed = set()
        new = []
        for song in added:
            labelid = song.get("labelid", "")
            for alb in song("album").split("\n"):
                key = alb + "\u0000" + labelid
                if key not in albums:
                    albums[key] = klass._Album(alb, labelid)
                    new.append(albums[key])
                albums[key].songs.add(song)
                changed.add(alb)
        for album in new:
            album._model = model
            album._iter = model.append(row=[album])
        klass.__update(changed, model)
    __add_songs = classmethod(__add_songs)

    # Something like an AudioFile, but for a whole album.
    class _Album(object):
        __covers = {}
        __pending_covers = []

        def clear_cache(klass): klass.__covers.clear()
        clear_cache = classmethod(clear_cache)

        def __init__(self, title, labelid):
            self.length = 0
            self.discs = 1
            self.tracks = 0
            self.date = ""
            self.people = []
            self.title = title
            self.labelid = labelid
            self.songs = set()
            # cover = None indicates not gotten cover, cover = False
            # indicates a failure to find a cover.
            self.cover = self.__covers.get(self.title)
            self.genre = []

        def get(self, key, default=None):
            if key == "~#length": return self.length
            elif key == "~#tracks": return self.tracks
            elif key == "~#discs": return self.discs
            elif key == "~length": return self.__length
            elif key == "labelid": return self.labelid
            elif key == "date": return self.date
            elif key == "~#date":
                try: return int(self.date[:4])
                except (TypeError, ValueError): return 0
            elif key in ["cover", "~cover"]: return (self.cover and "y") or ""
            elif key in ["title", "album"]: return self.title
            elif key in ["people", "artist", "artists"]:
                return "\n".join(self.people)
            elif key == "genre": return self.genre
            elif key.startswith("~#") and key[-4:-3] != ":": key += ":avg"

            if key.startswith("~#") and key[-4:-3] == ":":
                # Using key.<func> runs the resulting list of values
                # through the function before returning it.
                func = key[-3:]
                key = key[:-4]
                func = {"max": max, "min": min, "sum": sum,
                        "avg": lambda s: float(sum(s)) / len(s)}.get(func)
                if func: return func([song(key, 0) for song in self.songs])
            return default

        __call__ = get

        # All songs added, cache info.
        def finalize(self):
            self.tracks = len(self.songs)
            self.length = 0
            people = {}
            genre = set()
            for song in self.songs:
                # Rank people by "relevance" -- artists before composers
                # before performers, then by number of appearances.
                for w, key in enumerate(ELPOEP):
                    for person in song.list(key):
                        people[person] = people.get(person, 0) - 1000 ** w
                genre.update(song("genre").split("\n"))

                self.discs = max(self.discs, song("~#disc", 0))
                self.length += song.get("~#length", 0)

            self.genre = "\n".join(filter(None, genre))
            self.people = [(num, person) for (person, num) in people.items()]
            self.people.sort()
            self.people = [person for (num, person) in self.people]
            self.__long_length = util.format_time_long(self.length)
            self.__length = util.format_time(self.length)

            if not self.title:
                self.date = ""
                self.discs = 1
            else: self.date = song.comma("date")

            if self.title: text = "<i><b>%s</b></i>" % util.escape(self.title)
            else: text = "<b>%s</b>" % _("Songs not in an album")
            if self.date: text += " (%s)" % self.date
            text += "\n<small>"
            if self.discs > 1:
                text += ngettext(
                    "%d disc", "%d discs", self.discs) % self.discs + " - "
            text += ngettext(
                "%d track", "%d tracks", self.tracks) % self.tracks
            text += " - " + self.__long_length
            text += "</small>\n" + ", ".join(map(util.escape, self.people))
            self.markup = text
            if self.title and self.cover is None:
                self.cover = False
                if not self.__pending_covers: gobject.idle_add(
                    self.__get_covers, priority=gobject.PRIORITY_LOW)
                self.__pending_covers.append([self.__get_cover, song])

        def remove(self, song):
            try: self.songs.remove(song)
            except KeyError: return False
            else: return True

        def __get_covers(self):
            try: get, song = self.__pending_covers.pop()
            except IndexError: return
            get(song)
            gobject.idle_add(self.__get_covers, priority=gobject.PRIORITY_LOW)

        def __get_cover(self, song):
            if self._iter is None: return
            cover = song.find_cover()
            if cover is not None:
                try:
                    cover = gtk.gdk.pixbuf_new_from_file_at_size(
                        cover.name, 48, 48)
                except: pass
                else:
                    # add a black outline
                    w, h = cover.get_width(), cover.get_height()
                    newcover = gtk.gdk.Pixbuf(
                        gtk.gdk.COLORSPACE_RGB, True, 8, w + 2, h + 2)
                    newcover.fill(0x000000ff)
                    cover.copy_area(0, 0, w, h, newcover, 1, 1)
                    self.cover = newcover
                    self.__covers[self.title] = newcover
                    self._model.row_changed(
                        self._model.get_path(self._iter), self._iter)

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
                else: self.__filter = Query(text).search
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
            cbmodel = gtk.ListStore(str, object)
            gtk.ComboBox.__init__(self, cbmodel)
            cell = gtk.CellRendererText()
            self.pack_start(cell, True)
            self.add_attribute(cell, 'text', 0)

            for text, func in [
                (_("Sort by title"), self.__compare_title),
                (_("Sort by artist"), self.__compare_artist),
                (_("Sort by date"), self.__compare_date),
                ]: cbmodel.append(row=[text, func])

            self.connect_object('changed', self.__set_cmp_func, model)
            try: active = config.getint('browsers', 'album_sort')
            except: active = 0
            self.set_active(active)

        def __set_cmp_func(self, model):
            active = self.get_active()
            config.set("browsers", "album_sort", str(active))
            model.set_default_sort_func(self.get_model()[(active,)][1])

        def __compare_title(self, model, i1, i2):
            a1, a2 = model[i1][0], model[i2][0]
            if (a1 and a2) is None: return cmp(a1, a2)
            elif not a1.title: return 1
            elif not a2.title: return -1
            else: return cmp(a1.title, a2.title) or cmp(a1.labelid, a2.labelid)

        def __compare_artist(self, model, i1, i2):
            a1, a2 = model[i1][0], model[i2][0]
            if (a1 and a2) is None: return cmp(a1, a2)
            elif not a1.title: return 1
            elif not a2.title: return -1
            else: return (cmp(a1.people and a1.people[0],
                              a2.people and a2.people[0]) or
                          cmp(a1.date, a2.date) or
                          cmp(a1.title, a2.title) or
                          cmp(a1.labelid, a2.labelid))

        def __compare_date(self, model, i1, i2):
            a1, a2 = model[i1][0], model[i2][0]
            if (a1 and a2) is None: return cmp(a1, a2)
            elif a1.title == "": return 1
            elif a2.title == "": return -1
            return (cmp(a1.date, a2.date) or
                    cmp(a1.title, a2.title) or
                    cmp(a1.labelid, a2.labelid))

    class _AlbumStore(gtk.ListStore):
        def get_albums(self):
            albums = [row[0] for row in self]
            try: albums.remove(None)
            except ValueError: pass
            return dict([(a.title + "\u0000" + a.labelid, a) for a in albums])

    def __init__(self, watcher, player):
        gtk.VBox.__init__(self, spacing=6)

        if self.__model is None: AlbumList._init_model(watcher)
        self.__save = bool(player)

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        view = HintedTreeView()
        view.set_headers_visible(False)
        model_sort = gtk.TreeModelSort(self.__model)
        model_filter = model_sort.filter_new()

        render = gtk.CellRendererPixbuf()
        column = gtk.TreeViewColumn("covers", render)
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
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw.add(view)
        e = self.FilterEntry(model_filter)

        if player: view.connect('row-activated', self.__play_selection, player)
        view.get_selection().connect('changed', self.__selection_changed, e)

        targets = [("text/x-quodlibet-songs", gtk.TARGET_SAME_APP, 1),
                   ("text/uri-list", 0, 2)]
        view.drag_source_set(
            gtk.gdk.BUTTON1_MASK, targets, gtk.gdk.ACTION_COPY)
        view.connect("drag-data-get", self.__drag_data_get)

        menu = gtk.Menu()
        button = gtk.ImageMenuItem(gtk.STOCK_REFRESH)
        props = gtk.ImageMenuItem(stock.EDIT_TAGS)
        info = gtk.ImageMenuItem(gtk.STOCK_INFO)
        queue = gtk.ImageMenuItem(stock.ENQUEUE)
        rem = gtk.ImageMenuItem(stock.REMOVE)
        menu.append(button)
        menu.append(queue)
        menu.append(rem)
        menu.append(props)
        menu.append(info)
        menu.show_all()
        button.connect('activate', self.__refresh_album, view.get_selection())
        queue.connect('activate', self.__enqueue, view)
        rem.connect('activate', self.__remove, view.get_selection(), watcher)
        props.connect('activate', self.__properties, view, watcher)
        info.connect('activate', self.__information, view, watcher)

        view.connect_object('popup-menu', self.__popup, menu)

        hb = gtk.HBox(spacing=6)
        hb.pack_start(self.SortCombo(model_sort), expand=False)
        hb.pack_start(e)
        self.pack_start(hb, expand=False)
        self.pack_start(sw, expand=True)
        view.set_model(model_filter)
        self.show_all()

    def __refresh_album(self, menuitem, selection):
        model, rows = selection.get_selected_rows()
        albums = [model[row][0] for row in rows]
        if None in albums:
            for row in model:
                if row[0]:
                    row[0].cover = None
                    row[0].finalize()
        else:
            for album in albums:
                album.cover = None
                album.finalize()

    def __remove(self, menuitem, selection, watcher):
        songs = self.__get_selected_songs(selection)
        if songs:
            map(library.remove, songs)
            watcher.removed(songs)
            selection.unselect_all()

    def __popup(self, menu):
        menu.popup(None, None, None, 0, gtk.get_current_event_time())
        return True

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
        if None in albums: albums = [row[0] for row in model if row[0]]
        songs = set()
        map(songs.update, [album.songs for album in albums])
        return list(songs)

    def __properties(self, activator, view, watcher):
        songs = self.__get_selected_songs(view.get_selection())
        if songs: SongProperties(watcher, songs)

    def __information(self, activator, view, watcher):
        songs = self.__get_selected_songs(view.get_selection())
        if songs: Information(watcher, songs)

    def __drag_data_get(self, view, ctx, sel, tid, etime):
        songs = self.__get_selected_songs(view.get_selection())
        songs.sort()
        if tid == 1:
            filenames = [song("~filename") for song in songs]
            sel.set("text/x-quodlibet-songs", 8, "\x00".join(filenames))
        else: sel.set_uris([song("~uri") for song in songs])
        
    def __enqueue(self, item, view):
        songs = self.__get_selected_songs(view.get_selection())
        songs.sort()
        from widgets import main
        main.playlist.enqueue(songs)

    def __play_selection(self, view, indices, col, player):
        player.reset()
        player.next()

    def filter(self, key, values):
        assert(key == "album")
        if not values: values = [""]
        view = self.get_children()[1].child
        selection = view.get_selection()
        selection.unselect_all()
        model = view.get_model()
        first = None
        for i, row in enumerate(iter(model)):
            if row[0] is not None and row[0].title in values:
                selection.select_path(i)
                first = first or i
        if first:
            view.scroll_to_cell(first, use_align=True, row_align=0.5)

    def activate(self):
        self.get_children()[1].child.get_selection().emit('changed')

    def can_filter(self, key):
        return (key == "album")

    def restore(self):
        albums = config.get("browsers", "albums").split("\n")
        selection = self.get_children()[1].child.get_selection()
        # FIXME: If albums is "" then it could be either all albums or
        # no albums. If it's "" and some other stuff, assume no albums,
        # otherwise all albums.
        selection.unselect_all()
        if albums == [""]:  selection.select_path((0,))
        else:
            model = selection.get_tree_view().get_model()
            first = None
            for i, row in enumerate(iter(model)):
                if row[0] is not None and row[0].title in albums:
                    selection.select_path(i)
                    first = first or i

            if first: selection.get_tree_view().scroll_to_cell(
                first, use_align=True, row_align=0.5)

    def scroll(self, song):
        view = self.get_children()[1].child
        model = view.get_model()
        values = song.list("album")
        for i, row in enumerate(iter(model)):
            if row[0] is not None and row[0].title in values:
                view.scroll_to_cell(i, use_align=True, row_align=0.5)
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

gobject.type_register(AlbumList)

browsers = [(4, _("_Album List"), AlbumList, True)]
