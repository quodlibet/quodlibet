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
import parser
import player
import qltk
import util
from widgets import widgets

if sys.version_info < (2, 4): from sets import Set as set
from library import library
from browsers.base import Browser
from properties import SongProperties
from gettext import ngettext

class AlbumList(Browser, gtk.VBox):
    expand = qltk.RHPaned
    __gsignals__ = Browser.__gsignals__

    # Something like an AudioFile, but for a whole album.
    class _Album(object):
        __covers = {}
        __pending_covers = []

        def clear_cache(klass): klass.__covers.clear()
        clear_cache = classmethod(clear_cache)

        def __init__(self, title):
            self.length = 0
            self.discs = 1
            self.tracks = 0
            self.date = ""
            self.people = set()
            self.title = title
            self.songs = set()
            self.cover = self.__covers.get(self.title, False)
            self.genre = set()

        def get(self, key, default=None):
            if key == "~#length": return self.length
            elif key == "~#tracks": return self.tracks
            elif key == "~#discs": return self.discs
            elif key == "~length": return self.__length
            elif key in ["title", "album"]: return self.title
            elif key == "date": return self.date
            elif key in ["people", "artist", "artists"]:
                return "\n".join(self.people)
            elif key in "genre":
                return "\n".join(self.genre)
            else: return default

        __call__ = get

        # All songs added, cache info.
        def finalize(self):
            self.tracks = len(self.songs)
            self.length = sum([song["~#length"] for song in self.songs])
            self.__long_length = util.format_time_long(self.length)
            self.__length = util.format_time(self.length)
            people = {}
            self.genre = set()
            for song in self.songs:
                for w, key in enumerate(["performer", "composer", "artist"]):
                    for person in song.list(key):
                        if person not in people:
                            people[person] = 0
                        people[person] -= 1000 ** w
                self.genre.update(song.list("genre"))
            self.people = [(num, person) for (person, num) in people.items()]
            self.people.sort()
            self.people = [person for (num, person) in self.people]

            if self.title:
                for song in self.songs:
                    if "date" in song:
                        try: self.date = song.list("date")[0]
                        except IndexError: pass
                    self.discs = max(self.discs, song("~#disc", 0))

            text = "<i><b>%s</b></i>" % util.escape(
                self.title or _("Songs not in an album"))
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

        def add(self, song):
            self.songs.add(song)
            if self.title:
                if self.cover is False:
                    self.cover = None
                    if not self.__pending_covers: gobject.idle_add(
                        self.__get_covers, priority=gobject.PRIORITY_LOW)
                    self.__pending_covers.append([self.__get_cover, song])

        def remove(self, song):
            try: self.songs.remove(song)
            except KeyError: return False
            else: return True

        def __nonzero__(self): return bool(self.songs)

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
    class FilterEntry(qltk.ValidatingEntry):
        def __init__(self, model):
            qltk.ValidatingEntry.__init__(self, parser.is_valid_color)
            self.connect_object('changed', self.__filter_changed, model)
            self.__refill_id = None
            self.__filter = None
            self.inhibit = False
            model.set_visible_func(self.__parse)

        def __parse(self, model, iter):
            if self.__filter is None: return True
            elif model[iter][0] is None: return False
            else: return self.__filter(model[iter][0])

        def __filter_changed(self, model):
            if self.__refill_id is not None:
                gobject.source_remove(self.__refill_id)
                self.__refill_id = None
            text = self.get_text().decode('utf-8')
            if parser.is_parsable(text):
                if not text: self.__filter = None
                else: self.__filter = parser.parse(text).search
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
                (_("Sort by artist"), self.__compare_artist)
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
            else: return cmp(a1.title, a2.title)

        def __compare_artist(self, model, i1, i2):
            a1, a2 = model[i1][0], model[i2][0]
            if (a1 and a2) is None: return cmp(a1, a2)
            elif a1.title == "": return 1
            elif a2.title == "": return -1
            else: return (cmp(a1.people, a2.people) or
                          cmp(a1.date, a2.date) or
                          cmp(a1.title, a2.title))

    class _AlbumStore(gtk.ListStore):
        def get_albums(self):
            albums = [row[0] for row in self]
            try: albums.remove(None)
            except ValueError: pass
            return dict([(a.title, a) for a in albums])

    def __init__(self, main=True):
        gtk.VBox.__init__(self)

        self.__save = main

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        view = qltk.HintedTreeView()
        view.set_headers_visible(False)
        model = self._AlbumStore(object)
        model_sort = gtk.TreeModelSort(model)
        model_filter = model_sort.filter_new()
        view.set_model(model_filter)

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

        if main: view.connect('row-activated', self.__play_selection)
        view.get_selection().connect('changed', self.__selection_changed, e)
        for s in [
            widgets.watcher.connect('removed', self.__remove_songs, model),
            widgets.watcher.connect('changed', self.__changed_songs, model),
            widgets.watcher.connect('added', self.__add_songs, model),
            ]:
            self.connect_object('destroy', widgets.watcher.disconnect, s)

        menu = gtk.Menu()
        button = gtk.ImageMenuItem(gtk.STOCK_REFRESH)
        props = gtk.ImageMenuItem(gtk.STOCK_PROPERTIES)
        menu.append(button)
        menu.append(props)
        menu.show_all()
        button.connect('activate', self.__refresh, view, model, True)
        props.connect('activate', self.__properties, view)

        view.connect_object('popup-menu', gtk.Menu.popup, menu,
                            None, None, None, 2, 0)
        view.connect('button-press-event', self.__button_press, menu)

        hb = gtk.HBox(spacing=6)
        hb.pack_start(self.SortCombo(model_sort), expand=False)
        hb.pack_start(e)
        self.pack_start(hb, expand=False)
        self.pack_start(sw, expand=True)
        self.__refresh(None, view, model)
        self.show_all()

    def __get_selected_albums(self, selection):
        model, rows = selection.get_selected_rows()
        if not model or not rows: return set([])
        albums = [model[row][0] for row in rows]
        if None in albums: return None
        else: return albums

    def __update(self, changed, model):
        to_change = []
        to_remove = []        
        def update(model, path, iter):
            album = model[iter][0]
            if album is not None and album.title in changed:
                if album: to_change.append((path, iter))
                else: to_remove.append(iter)
                album.finalize()
        model.foreach(update)
        if to_change: map(model.row_changed, *zip(*to_change))
        if to_remove: map(model.remove, to_remove)

    def __remove_songs(self, watcher, removed, model):
        albums = model.get_albums()
        changed = set()
        for title, album in albums.iteritems():
            if True in map(album.remove, removed): changed.add(title)
        self.__update(changed, model)

    def __changed_songs(self, watcher, changed, model):
        self.__remove_songs(watcher, changed, model)
        self.__add_songs(watcher, changed, model)

    def __add_songs(self, watcher, added, model):
        albums = model.get_albums()
        changed = set()
        new = []
        for song in added:
            if "album" in song:
                for alb in song.list("album"):
                    if alb in albums:
                        changed.add(alb)
                        albums[alb].add(song)
                    else:
                        albums[alb] = self._Album(alb)
                        new.append(albums[alb])
                        albums[alb].add(song)
            else:
                if "" not in albums:
                    albums[""] = self._Album("")
                    new.append(albums[""])
                changed.add("")
                albums[""].add(song)
        for album in new:
            album.finalize()
            album._model = model
            album._iter = model.append(row=[album])
        self.__update(changed, model)

    def __get_selected_songs(self, selection):
        model, rows = selection.get_selected_rows()
        if not model or not rows: return set([])
        albums = [model[row][0] for row in rows]
        if None in albums: return library.values()
        else: return list(
            reduce(set.union, [album.songs for album in albums], set()))

    def __properties(self, activator, view):
        songs = self.__get_selected_songs(view.get_selection())
        if songs:
            songs.sort()
            SongProperties(songs, widgets.watcher, initial=0)

    def __button_press(self, view, event, menu):
        x, y = map(int, [event.x, event.y])
        try: path, col, cellx, celly = view.get_path_at_pos(x, y)
        except TypeError: return True
        if event.button == 3:
            sens = bool(view.get_model()[path][0])
            for c in menu.get_children(): c.set_sensitive(sens)
            view.grab_focus()
            selection = view.get_selection()
            if not selection.path_is_selected(path):
                view.set_cursor(path, col, 0)
            menu.popup(None, None, None, event.button, event.time)
            return True

    def __play_selection(self, view, indices, col):
        player.playlist.reset()
        player.playlist.next()

    def filter(self, key, values):
        assert(key == "album")
        if not values: values = [""]
        view = self.get_children()[1].child
        selection = view.get_selection()
        selection.unselect_all()
        model = view.get_model()
        first = None
        for i, row in enumerate(iter(model)):
            if row[0] and row[0].title in values:
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
                if row[0] and row[0].title in albums:
                    selection.select_path(i)
                    first = first or i

            if first: selection.get_tree_view().scroll_to_cell(
                first, use_align=True, row_align=0.5)

    def scroll(self):
        view = self.get_children()[1].child
        model = view.get_model()
        values = widgets.watcher.song.list("album")
        for i, row in enumerate(iter(model)):
            if row[0] and row[0].title in values:
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

    def __refresh(self, watcher, view, model, clear_cache=False):
        # Prevent refiltering while the view is being refreshed.
        view.freeze_child_notify()
        selected = self.__get_selected_albums(view.get_selection())
        if selected is not None: selected = [a.title for a in selected]

        if clear_cache: self._Album.clear_cache()
        for row in iter(model):
            if row[0]: row[0]._iter = row[0]._model = None
        model.clear()
        albums = {}
        songs = library.itervalues()
        for song in songs:
            if "album" not in song:
                if "" not in albums: albums[""] = self._Album("")
                albums[""].add(song)
            else:
                for album in song.list('album'):
                    if album not in albums:
                        albums[album] = self._Album(album)
                    albums[album].add(song)

        model.append(row=[None])
        for album in albums.values():
            album.finalize()
            album._iter = model.append(row=[album])
            album._model = model

        view.thaw_child_notify()
        if selected: self.filter("album", selected)

gobject.type_register(AlbumList)

browsers = [(4, _("_Album List"), AlbumList, True)]
