# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import sys
import gobject, gtk, pango
import config
import const
import qltk
import util
import stock
from qltk.completion import EntryWordCompletion
from qltk.views import AllTreeView
from qltk.entry import ValidatingEntry
from qltk.ccb import ConfigCheckButton
from qltk.textedit import PatternEditBox
from parse import Query, XMLFromPattern
from formats._audio import PEOPLE
ELPOEP = list(PEOPLE); ELPOEP.reverse()

if sys.version_info < (2, 4): from sets import Set as set
from library import library
from browsers._base import Browser
from qltk.properties import SongProperties
from qltk.information import Information

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
        f = qltk.Frame(label=_("Album Display"), bold=True, child=vbox)
        self.child.pack_start(f)

        self.child.show_all()

    def __delete_event(self, event):
        self.hide()
        return True

    def __set_pattern(self, apply, edit):
        AlbumList.refresh_pattern(edit.text)

    def __preview_pattern(self, edit, label):
        from util import tag
        album = AlbumList._Album(tag("album"), tag("labelid"))
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

    def init(klass, watcher):
        pattern_fn = os.path.join(const.DIR, "album_pattern")
        try:
            klass._Album._pattern_text = file(pattern_fn).read().rstrip()
        except EnvironmentError: pass
        else:
            klass._Album._pattern = XMLFromPattern(klass._Album._pattern_text)
    init = classmethod(init)

    def toggle_covers(klass):
        on = config.getboolean("browsers", "album_covers")
        for albumlist in klass.instances():
            albumlist.__cover_column.set_visible(on)
    toggle_covers = classmethod(toggle_covers)

    def refresh_pattern(klass, pattern_text):
        if pattern_text == klass._Album._pattern_text: return
        klass._Album._pattern_text = pattern_text
        klass._Album._pattern = XMLFromPattern(pattern_text)
        for row in klass.__model:
            album = row[0]
            if album is not None:
                album.markup = album._pattern % album
                klass.__model.row_changed(row.path, row.iter)
        pattern_fn = os.path.join(const.DIR, "album_pattern")
        f = file(pattern_fn, "w")
        f.write(pattern_text  + "\n")
        f.close()
    refresh_pattern = classmethod(refresh_pattern)

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
        to_update = klass.__remove_songs(watcher, changed, model, False)
        to_update.update(klass.__add_songs(watcher, changed, model, False))
        klass.__update(to_update, model)
    __changed_songs = classmethod(__changed_songs)

    def __update(klass, changed, model):
        to_change = []
        to_remove = []
        for row in model:
            album = row[0]
            if album is not None and album.title in changed:
                if album.songs:
                    to_change.append((row.path, row.iter))
                    album.finalize()
                else:
                    to_remove.append(row.iter)
                    album._model = album._iter = None
        if to_change: map(model.row_changed, *zip(*to_change))
        if to_remove: map(model.remove, to_remove)
    __update = classmethod(__update)

    def __remove_songs(klass, watcher, removed, model, update=True):
        albums = model.get_albums()
        changed = set()
        for album in albums.itervalues():
            if True in map(album.remove, removed): changed.add(album.title)
        if update: klass.__update(changed, model)
        else: return changed
    __remove_songs = classmethod(__remove_songs)

    def __add_songs(klass, watcher, added, model, update=True):
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
        if update: klass.__update(changed, model)
        else: return changed
    __add_songs = classmethod(__add_songs)

    # Something like an AudioFile, but for a whole album.
    class _Album(object):
        __covers = {}
        __pending_covers = []

        _pattern_text = PATTERN
        _pattern = XMLFromPattern(PATTERN)

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
            self.genre = u""

        def get(self, key, default="", connector=u" - "):
            if "~" in key[1:]:
                return connector.join(map(self.get, util.tagsplit(key)))
            elif key == "~#length": return self.length
            elif key == "~#tracks": return self.tracks
            elif key == "~#discs": return self.discs
            elif key == "~length": return util.format_time(self.length)
            elif key == "~long-length":
                return util.format_time_long(self.length)
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
            elif key == "~tracks":
                return ngettext(
                    "%d track", "%d tracks", self.tracks) % self.tracks
            elif key == "~discs":
                if self.discs > 1:
                    return ngettext(
                        "%d disc", "%d discs", self.discs) % self.discs
                else: return default

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
        def comma(self, *args): return self.get(*args).replace("\n", ", ")

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
            self.people = [person for (num, person) in self.people[:100]]
            self.__long_length = util.format_time_long(self.length)
            self.__length = util.format_time(self.length)

            if not self.title:
                self.date = ""
                self.discs = 1
            else: self.date = song.comma("date")

            self.markup = self._pattern % self

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
        self._register_instance()
        if self.__model is None: AlbumList._init_model(watcher)
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
        view.connect_object('popup-menu', self.__popup, view, watcher)

        hb = gtk.HBox(spacing=6)
        hb.pack_start(self.SortCombo(model_sort), expand=False)
        hb.pack_start(e)
        prefs = gtk.Button()
        prefs.add(
            gtk.image_new_from_stock(gtk.STOCK_PREFERENCES, gtk.ICON_SIZE_MENU))
        prefs.connect('clicked', self.__preferences)
        hb.pack_start(prefs, expand=False)
        self.pack_start(hb, expand=False)
        self.pack_start(sw, expand=True)
        view.set_model(model_filter)
        self.show_all()
        
    def __popup(self, view, watcher):
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
        # Build plugins Menu
        songs = self.__get_selected_songs(view.get_selection())
        songs.sort()
        
        submenu = self.pm.create_plugins_menu(songs)
        if submenu is not None:
            b = gtk.ImageMenuItem(stock.PLUGINS)
            menu.append(b)
            b.set_submenu(submenu)
        menu.show_all()
        
        button.connect('activate', self.__refresh_album, view.get_selection())
        queue.connect('activate', self.__enqueue, view)
        rem.connect('activate', self.__remove, view.get_selection(), watcher)
        props.connect('activate', self.__properties, view, watcher)
        info.connect('activate', self.__information, view, watcher)
        menu.connect_object('selection-done', gtk.Menu.destroy, menu)
        menu.popup(None, None, None, 0, gtk.get_current_event_time())
        return True

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
        songs.sort()
        if songs: SongProperties(watcher, songs)

    def __information(self, activator, view, watcher):
        songs = self.__get_selected_songs(view.get_selection())
        songs.sort()
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
                first = first or row.path[0]
        if first:
            view.scroll_to_cell(first, use_align=True, row_align=0.5)

    def activate(self):
        self.get_children()[1].child.get_selection().emit('changed')

    def can_filter(self, key):
        return (key == "album")

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
        for row in model:
            if row[0] is not None and row[0].title in values:
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

gobject.type_register(AlbumList)

browsers = [(4, _("_Album List"), AlbumList, True)]
