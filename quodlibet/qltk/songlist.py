# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, sys
import random
import locale
import time, datetime

import gobject, gtk, pango

import stock
import qltk
import player
import util; from util import tag
from library import library
from qltk.properties import SongProperties
from qltk.information import Information
from qltk.views import AllTreeView
from qltk.delete import DeleteDialog
from parse import Query

if sys.version_info < (2, 4): from sets import Set as set

OFF, SHUFFLE, WEIGHTED, ONESONG = range(4)

class PlaylistMux(object):
    def __init__(self, watcher, q, pl):
        self.q = q
        self.pl = pl
        watcher.connect('song-started', self.__check_q)

    def __check_q(self, watcher, song):
        if song is not None:
            iter = self.q.find(song)
            if iter: self.q.remove(iter)
            self.q.go_to(None)

    def get_current(self):
        if self.q.current is not None: return self.q.current
        else: return self.pl.current

    current = property(get_current)

    def next(self):
        if self.q.is_empty(): self.pl.next()
        elif self.q.current is None: self.q.next()

    def next_ended(self):
        if self.q.is_empty(): self.pl.next_ended()
        elif self.q.current is None: self.q.next()

    def previous(self):
        self.pl.previous()

    def go_to(self, song):
        self.pl.go_to(song)
        self.q.go_to(None)

    def reset(self):
        self.pl.reset()

    def enqueue(self, songs):
        for song in songs: self.q.append(row=[song])

class PlaylistModel(gtk.ListStore):
    order = OFF
    repeat = False
    __path = None
    __old_value = None
    __sig = None

    __gsignals__ = {
        'songs-set': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ())
        }

    def __init__(self):
        gtk.ListStore.__init__(self, object)
        self.__played = []

    def set(self, songs):
        if self.__sig is not None:
            gobject.source_remove(self.__sig)
            self.__sig = None

        oldsong = self.current
        if oldsong is None: oldsong = self.__old_value
        else: self.__old_value = oldsong
        self.__played = []
        self.__path = None
        self.clear()
        songs = songs[:]
        if self.__set_idle(oldsong, songs):
            self.__sig = gobject.idle_add(self.__set_idle, oldsong, songs)

    def __set_idle(self, oldsong, songs):
        to_add = songs[:100]
        del(songs[:100])
        for song in to_add:
            iter = self.append(row=[song])
            if song == oldsong: self.__path = self.get_path(iter)[0]
        if songs: return True
        else:
            if self.current is not None: self.__old_value = None
            self.__sig = None
            self.emit('songs-set')
            return False

    def remove(self, iter):
        oldpath = self.__path
        iterpath = self.get_path(iter)[0]
        gtk.ListStore.remove(self, iter)
        if self.is_empty(): self.__path = None
        elif oldpath >= iterpath:
            # If the iter removed was before the path, we decrease
            # by one. Otherwise, we're still the same path.
            self.__path = min(oldpath, len(self)) - 1

    def get(self):
        return [row[0] for row in self]

    def get_current(self):
        if self.__path is None: return None
        elif self.is_empty(): return None
        else: return self[(self.__path,)][0]

    current = property(get_current)

    def get_current_path(self):
        if self.__path is None: return None
        elif self.is_empty(): return None
        else: return (self.__path,)
    current_path = property(get_current_path)

    def get_current_iter(self):
        if self.__path is None: return None
        elif self.is_empty(): return None
        else: return self.get_iter(self.__path)
    current_iter = property(get_current_iter)

    def next(self):
        if self.order in [WEIGHTED, SHUFFLE]:
            self.__next_shuffle()
            return
        
        # If we're empty, the next song is no song.
        # If the current song is the last song,
        #  - If repeat is off, the next song is no song.
        #  - If repeat is on, the next song is the first song.
        # Else, if the current song is no song, the next song is the first.
        # Else, the next song is the next song.
        if self.is_empty(): self.__path = None
        elif self.__path >= len(self) - 1:
            if self.repeat: self.__path = 0
            else: self.__path = None
        elif self.__path is None: self.__path = 0
        else:
            self.__path += 1

    def next_ended(self):
        if self.order != ONESONG: self.next()
        elif not self.repeat: self.__path = None

    def __next_shuffle(self):
        if self.__path is not None:
            self.__played.append(self.__path)

        if self.order == SHUFFLE: self.__next_shuffle_regular()
        elif self.order == WEIGHTED: self.__next_shuffle_weighted()
        else: raise ValueError("Invalid shuffle %d" % self.order)

    def __next_shuffle_regular(self):
        played = set(self.__played)
        songs = set(range(len(self)))
        remaining = songs.difference(played)
        if remaining:
            self.__path = random.choice(list(remaining))
        elif self.repeat:
            self.__played = []
            self.__path = random.choice(list(songs))
        else:
            self.__played = []
            self.__path = None

    def __next_shuffle_weighted(self):
        songs = self.get()
        max_score = sum([song.get('~#rating', 2) for song in songs])
        choice = random.random() * max_score
        current = 0.0
        for i, song in enumerate(songs):
            current += song.get("~#rating", 2)
            if current >= choice:
                self.__path = i
                break

        else: self.__path = 0

    def previous(self):
        if self.order in [SHUFFLE, WEIGHTED]:
            self.__previous_shuffle()
            return

        # If we're empty, the last song is no song.
        # Else if the current song is none, the previous is the last.
        # Else the previous song is the previous song.
        if self.is_empty(): self.__path = None
        elif self.__path == 0: pass
        elif self.__path is None: self.__path = len(self) - 1
        else: self.__path  = max(0, self.__path - 1)

    def __previous_shuffle(self):
        try: path = self.__played.pop(-1)
        except IndexError: pass
        else: self.__path = path

    def go_to(self, song):
        if self.order and self.__path is not None:
            self.__played.append(self.__path)

        self.__path = None
        if isinstance(song, gtk.TreeIter):
            self.__path = self.get_path(song)[0]
        else:
            for row in self:
                if row[0] == song:
                    self.__path = row.path[0]
                    break

    def find(self, song):
        for row in self:
            if row[0] == song: return row.iter
        return None

    def find_all(self, songs):
        return [row.iter for row in self if row[0] in songs]

    def __contains__(self, song): return bool(self.find(song))

    def is_empty(self):
        return not bool(len(self))

    def reset(self):
        self.__played = []
        self.go_to(None)

    def insert_before(self, iter, row):
        citer = self.current_iter
        r = super(PlaylistModel, self).insert_before(iter, row)
        if citer is not None: self.__path = self.get_path(citer)[0]
        return r

    def insert_after(self, iter, row):
        citer = self.current_iter
        r = super(PlaylistModel, self).insert_after(iter, row)
        if citer is not None: self.__path = self.get_path(citer)[0]
        return r

    def move_before(self, iter, position):
        citer = self.current_iter
        super(PlaylistModel, self).move_before(iter, position)
        if citer is not None: self.__path = self.get_path(citer)[0]

    def move_after(self, iter, position):
        citer = self.current_iter
        super(PlaylistModel, self).move_after(iter, position)
        if citer is not None: self.__path = self.get_path(citer)[0]

gobject.type_register(PlaylistModel)

class SongList(AllTreeView):
    # A TreeView containing a list of songs.

    # When created SongLists add themselves to this dict so they get
    # informed when headers are updated.
    __songlistviews = {}

    headers = [] # The list of current headers.
    star = list(Query.STAR)

    CurrentColumn = None

    class TextColumn(gtk.TreeViewColumn):
        # Base class for other kinds of columns.
        _render = gtk.CellRendererText()

        def _cdf(self, column, cell, model, iter, tag):
            try:
                song = model[iter][0]
                cell.set_property('text', song.comma(tag))
            except AttributeError: pass

        def __init__(self, t):
            gtk.TreeViewColumn.__init__(self, tag(t), self._render)
            self.header_name = t
            self.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
            self.set_visible(True)
            self.set_clickable(True)
            self.set_sort_indicator(False)
            self.set_cell_data_func(self._render, self._cdf, t)

    class DateColumn(TextColumn):
        # The '~#' keys that are dates.
        def _cdf(self, column, cell, model, iter, tag):
            try:
                stamp = model[iter][0](tag)
                if not stamp: cell.set_property('text', _("Never"))
                else:
                    date = datetime.datetime.fromtimestamp(stamp).date()
                    today = datetime.datetime.now().date()
                    days = (today - date).days
                    stamp = time.localtime(stamp)
                    if days == 0: rep = time.strftime("%X", stamp).decode(
                        locale.getpreferredencoding())
                    elif days < 7: rep = time.strftime("%A", stamp).decode(
                        locale.getpreferredencoding())
                    else: rep = time.strftime("%x", stamp).decode(
                        locale.getpreferredencoding())
                    cell.set_property('text', rep)
            except AttributeError: pass

    class WideTextColumn(TextColumn):
        # Resizable and ellipsized at the end. Used for any key with
        # a '~' in it, and 'title'.
        _render = gtk.CellRendererText()
        _render.set_property('ellipsize', pango.ELLIPSIZE_END)

        def __init__(self, tag):
            SongList.TextColumn.__init__(self, tag)
            self.set_expand(True)
            self.set_resizable(True)
            self.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            self.set_fixed_width(1)

    class RatingColumn(TextColumn):
        # Render ~#rating directly (simplifies filtering, saves
        # a function call).
        def _cdf(self, column, cell, model, iter, tag):
            try:
                song = model[iter][0]
                cell.set_property(
                    'text', util.format_rating(song.get("~#rating", 0.5)))
            except AttributeError: pass

        def __init__(self):
            SongList.TextColumn.__init__(self, "~#rating")
            self.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)

            # Neither of TreeViewColumn or CellRendererText is a GTK
            # widget, so we need a new one to use Pango. Lame.
            l = gtk.Label(util.format_rating(1.0))
            # Magic offset constant tested on Sans 10 to Sans 26.
            min_width = l.size_request()[0] + 10
            l.destroy()
            self.set_min_width(min_width)

    class NonSynthTextColumn(WideTextColumn):
        # Optimize for non-synthesized keys by grabbing them directly.
        # Used for any tag without a '~' except 'title'.
        def _cdf(self, column, cell, model, iter, tag):
            try:
                song = model[iter][0]
                cell.set_property(
                    'text', song.get(tag, "").replace("\n", ", "))
            except AttributeError: pass

    class FSColumn(WideTextColumn):
        # Contains text in the filesystem encoding, so needs to be
        # decoded safely (and also more slowly).
        def _cdf(self, column, cell, model, iter, tag, code=util.fscoding):
            try:
                song = model[iter][0]
                cell.set_property('text', util.unexpand(
                    song.comma(tag).decode(code, 'replace')))
            except AttributeError: pass

    class LengthColumn(TextColumn):
        _render = gtk.CellRendererText()
        _render.set_property('xalign', 1.0)
        def _cdf(self, column, cell, model, iter, tag):
            try:
                song = model[iter][0]
                cell.set_property(
                    'text', util.format_time(song.get("~#length", 0)))
            except AttributeError: pass

        def __init__(self, tag="~#length"):
            SongList.TextColumn.__init__(self, tag)
            self.set_alignment(1.0)

    class NumericColumn(TextColumn):
        # Any '~#' keys except dates.
        _render = gtk.CellRendererText()
        _render.set_property('xpad', 12)
        _render.set_property('xalign', 1.0)

    class PatternColumn(WideTextColumn):
        def _cdf(self, column, cell, model, iter, tag):
            try:
                song = model[iter][0]
                cell.set_property('text', self.__pattern % song)
            except AttributeError: pass

        def __init__(self, pattern):
            SongList.WideTextColumn.__init__(self, pattern)
            from parse import Pattern
            self.__pattern = Pattern(pattern)

    def Menu(self, header, browser, watcher):
        songs = self.get_selected_songs()
        if not songs: return
        header = util.tagsplit(header)[0]

        menu = browser.Menu(songs, self)
        if menu is None: menu = gtk.Menu()
        can_filter = browser.can_filter

        def Filter(t):
            # Translators: The substituted string is the name of the
            # selected column (a translated tag name).
            b = qltk.MenuItem(
                _("_Filter on %s") % tag(t, True), gtk.STOCK_INDEX)
            b.connect_object('activate', self.__filter_on, t, songs, browser)
            return b

        if header == "~#rating":
            item = gtk.MenuItem(_("_Rating"))
            m2 = gtk.Menu()
            item.set_submenu(m2)
            for i in range(0, int(1.0/util.RATING_PRECISION)+1):
                i *= util.RATING_PRECISION
                itm = gtk.MenuItem("%0.2f\t%s" % (i, util.format_rating(i)))
                m2.append(itm)
                itm.connect_object(
                    'activate', self.__set_rating, i, songs, watcher)
            menu.append(item)

        if (menu.get_children() and
            not isinstance(menu.get_children()[-1], gtk.SeparatorMenuItem)):
            menu.append(gtk.SeparatorMenuItem())

        if can_filter("artist"): menu.append(Filter("artist"))
        if can_filter("album"): menu.append(Filter("album"))
        if (header not in ["artist", "album"] and can_filter(header)):
            menu.append(Filter(header))

        if (menu.get_children() and
            not isinstance(menu.get_children()[-1], gtk.SeparatorMenuItem)):
            menu.append(gtk.SeparatorMenuItem())

        submenu = self.pm.create_plugins_menu(songs)
        if submenu is not None:
            b = gtk.ImageMenuItem(stock.PLUGINS)
            menu.append(b)
            b.set_submenu(submenu)

            if (menu.get_children() and
                not isinstance(menu.get_children()[-1],
                               gtk.SeparatorMenuItem)):
                menu.append(gtk.SeparatorMenuItem())

        buttons = []

        in_lib = True
        can_add = True
        is_file = True
        for song in songs:
            if song.get("~filename") not in library: in_lib = False
            if not song.can_add: can_add = False
            if not song.is_file: is_file = False


        import browsers
        try: playlists = browsers.playlists.Playlists.playlists()
        except AttributeError: pass
        else:            
            b = qltk.MenuItem(_("_Add to Playlist"), gtk.STOCK_ADD)
            menu.append(b)
            b.set_sensitive(can_add)
            submenu = gtk.Menu()
            i = gtk.MenuItem(_("_New Playlist"))
            i.connect('activate', self.__add_to_playlist, None, songs)
            submenu.append(i)
            submenu.append(gtk.SeparatorMenuItem())
        
            for playlist in playlists:
                i = gtk.MenuItem(playlist.name)
                i.connect('activate', self.__add_to_playlist, playlist, songs)
                submenu.append(i)
            b.set_submenu(submenu)
        
        b = gtk.ImageMenuItem(stock.ENQUEUE)
        b.connect('activate', self.__enqueue, songs)
        b.add_accelerator(
            'activate', self.accelerators, ord('Q'), 0, gtk.ACCEL_VISIBLE)
        menu.append(b)
        buttons.append(b)
        b.set_sensitive(can_add)

        menu.append(gtk.SeparatorMenuItem())

        b = gtk.ImageMenuItem(stock.REMOVE)
        b.connect('activate', self.__remove, songs, watcher)
        menu.append(b)
        buttons.append(b)
        b.set_sensitive(in_lib)

        b = gtk.ImageMenuItem(gtk.STOCK_DELETE)
        b.connect('activate', self.__delete, songs, watcher)
        menu.append(b)
        buttons.append(b)
        b.set_sensitive(is_file)

        b = gtk.ImageMenuItem(stock.EDIT_TAGS)
        key, val = gtk.accelerator_parse("<alt>Return")
        b.add_accelerator(
            'activate', self.accelerators, key, val, gtk.ACCEL_VISIBLE)
        b.connect_object('activate', SongProperties, watcher, songs)
        menu.append(b)

        try: b = gtk.ImageMenuItem(gtk.STOCK_INFO)
        except AttributeError: b = gtk.ImageMenuItem(gtk.STOCK_DIALOG_INFO)
        b.connect_object('activate', Information, watcher, songs)
        menu.append(b)

        menu.connect_object('selection-done', gtk.Menu.destroy, menu)
        menu.show_all()
        return menu

    def __add_to_playlist(self, activator, playlist, songs):
        import browsers
        if playlist is None:
            if len(songs) == 1: title = songs[0].comma("title")
            else: title = _("%(title)s and %(count)d more") % (
                {'title':songs[0].comma("title"), 'count':len(songs) - 1})
            playlist = browsers.playlists.Playlist.new(title)
        playlist.extend(songs)
        browsers.playlists.Playlists.changed(playlist)

    def __init__(self, watcher):
        super(SongList, self).__init__()
        self.set_model(PlaylistModel())
        self.set_size_request(200, 150)
        self.set_rules_hint(True)
        self.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.__songlistviews[self] = None     # register self
        self.set_column_headers(self.headers)
        self.connect_object('destroy', SongList.__destroy, self)
        sigs = [watcher.connect('changed', self.__song_updated),
                watcher.connect('removed', self.__song_removed),
                watcher.connect('paused', self.__redraw_current),
                watcher.connect('unpaused', self.__redraw_current)
                ]
        for sig in sigs:
            self.connect_object('destroy', watcher.disconnect, sig)

        self.connect('button-press-event', self.__button_press, watcher)
        self.connect('key-press-event', self.__key_press, watcher)

        self.disable_drop()
        self.connect('drag-motion', self.__drag_motion)
        self.connect('drag-data-get', self.__drag_data_get, watcher)
        self.connect('drag-data-received', self.__drag_data_received)

        # Enabling this screws up rating and enqueuing
        #self.set_search_column(0)
        #self.set_search_equal_func(self.__search_func)

        self.accelerators = gtk.AccelGroup()
        key, mod = gtk.accelerator_parse("<alt>Return")
        self.accelerators.connect_group(
            key, mod, 0, lambda *args: self.__song_properties(watcher))
        self.accelerators.connect

    def __search_func(self, model, column, key, iter, *args):
        for column in self.get_columns():
            value = model[iter][0](column.header_name)
            if not isinstance(value, basestring): continue
            elif key in value.lower() or key in value: return False
        else: return True

    def enable_drop(self):
        targets = [("text/x-quodlibet-songs", gtk.TARGET_SAME_APP, 1),
                   ("text/uri-list", 0, 2)]
        self.drag_source_set(
            gtk.gdk.BUTTON1_MASK, targets,
            gtk.gdk.ACTION_COPY|gtk.gdk.ACTION_MOVE)
        self.drag_dest_set(gtk.DEST_DEFAULT_ALL, targets,
                           gtk.gdk.ACTION_COPY|gtk.gdk.ACTION_MOVE)

    def disable_drop(self):
        targets = [("text/x-quodlibet-songs", gtk.TARGET_SAME_APP, 1),
                   ("text/uri-list", 0, 2)]
        self.drag_source_set(
            gtk.gdk.BUTTON1_MASK, targets, gtk.gdk.ACTION_COPY)
        self.drag_dest_unset()

    def __drag_motion(self, view, ctx, x, y, time):
        try: self.set_drag_dest_row(*self.get_dest_row_at_pos(x, y))
        except TypeError:
            if len(self.get_model()) == 0: path = 0
            else: path = len(self.get_model()) - 1
            self.set_drag_dest_row(path, gtk.TREE_VIEW_DROP_AFTER)
        if ctx.get_source_widget() == self: kind = gtk.gdk.ACTION_MOVE
        else: kind = gtk.gdk.ACTION_COPY
        ctx.drag_status(kind, time)
        return True

    def __drag_data_delete(self, view, ctx):
        map(view.get_model(), self.__drag_iters)
        self.__drag_iters = []

    def __drag_data_get(self, view, ctx, sel, tid, etime, watcher):
        model, paths = self.get_selection().get_selected_rows()
        if tid == 1:
            songs = [model[path][0] for path in paths
                     if model[path][0].can_add]
            if len(songs) != len(paths):
                qltk.ErrorMessage(
                    qltk.get_top_parent(self), _("Unable to copy songs"),
                    _("The files selected cannot be copied to other "
                      "song lists or the queue.")).run()
                ctx.drag_abort(etime)
                return
            added = filter(library.add_song, songs)
            filenames = [song("~filename") for song in songs]
            sel.set("text/x-quodlibet-songs", 8, "\x00".join(filenames))
            if added: watcher.added(added)
            if ctx.action == gtk.gdk.ACTION_MOVE:
                self.__drag_iters = map(model.get_iter, paths)
            else: self.__drag_iters = []
        else:
            uris = [model[path][0]("~uri") for path in paths]
            sel.set_uris(uris)
            self.__drag_iters = []

    def __drag_data_received(self, view, ctx, x, y, sel, info, etime):
        model = view.get_model()
        if info == 1:
            filenames = sel.data.split("\x00")
            move = (ctx.get_source_widget() == view)
        elif info == 2:
            from urllib import splittype as split, url2pathname as topath
            filenames = [os.path.normpath(topath(split(s)[1]))
                         for s in sel.get_uris()]
            move = False
        else:
            ctx.finish(False, False, etime)
            return

        songs = filter(None, map(library.get, filenames))
        if not songs:
            ctx.finish(bool(not filenames), False, etime)
            return

        try: path, position = view.get_dest_row_at_pos(x, y)
        except TypeError:
            path = max(0, len(model) - 1)
            position = gtk.TREE_VIEW_DROP_AFTER

        if move and ctx.get_source_widget() == view:
            iter = model.get_iter(path) # model can't be empty, we're moving
            if position in (gtk.TREE_VIEW_DROP_BEFORE,
                            gtk.TREE_VIEW_DROP_INTO_OR_BEFORE):
                while self.__drag_iters:
                    model.move_before(self.__drag_iters.pop(0), iter)
            else:
                while self.__drag_iters:
                    model.move_after(self.__drag_iters.pop(), iter)
            ctx.finish(True, False, etime)
        else:
            song = songs.pop(0)
            try: iter = model.get_iter(path)
            except ValueError: iter = model.append(row=[song]) # empty model
            else:
                if position in (gtk.TREE_VIEW_DROP_BEFORE,
                                gtk.TREE_VIEW_DROP_INTO_OR_BEFORE):
                    iter = model.insert_before(iter, [song])
                else: iter = model.insert_after(iter, [song])
            for song in songs:
                iter = model.insert_after(iter, [song])
            ctx.finish(True, move, etime)

    def __filter_on(self, header, songs, browser):
        if not browser or not browser.can_filter(header): return
        if songs is None:
            if player.playlist.song: songs = [player.playlist.song]
            else: return

        values = set()
        if header.startswith("~#"):
            values.update([song(header, 0) for song in songs])
        else:
            for song in songs: values.update(song.list(header))
        browser.filter(header, list(values))

    def __button_press(self, view, event, watcher):
        if event.button != 1: return
        x, y = map(int, [event.x, event.y])
        try: path, col, cellx, celly = view.get_path_at_pos(x, y)
        except TypeError: return True
        if col.header_name == "~#rating":
            song = view.get_model()[path][0]
            l = gtk.Label()
            l.set_text(util.format_rating(util.RATING_PRECISION))
            width = l.size_request()[0]
            l.destroy()
            count = int(float(cellx - 5) / width) + 1
            rating = max(0.0, min(1.0, count * util.RATING_PRECISION))
            if (rating <= util.RATING_PRECISION and
                song["~#rating"] == util.RATING_PRECISION): rating = 0
            self.__set_rating(rating, [song], watcher)

    def __remove(self, item, songs, watcher):
        # User requested that the selected songs be removed.
        map(library.remove, songs)
        watcher.removed(songs)

    def __enqueue(self, item, songs):
        songs = filter(lambda s: s.can_add, songs)
        if songs:
            from widgets import main, watcher
            added = filter(library.add_song, songs)
            main.playlist.enqueue(songs)
            if added: watcher.added(added)

    def __delete(self, item, songs, watcher):
        files = [song["~filename"] for song in songs]
        d = DeleteDialog(self, files)
        removed = d.run()
        d.destroy()
        removed = filter(None, map(library.get, removed))
        if removed:
            map(library.remove, removed)
            watcher.removed(removed)

    def __set_rating(self, value, songs, watcher):
        for song in songs: song["~#rating"] = value
        watcher.changed(songs)

    def __key_press(self, songlist, event, watcher):
        if event.string in ['0', '1', '2', '3', '4']:
            rating = min(1.0, int(event.string) * util.RATING_PRECISION)
            self.__set_rating(rating, self.get_selected_songs(), watcher)
        elif event.string == 'Q':
            self.__enqueue(None, self.get_selected_songs())

    def __redraw_current(self, watcher, song=None):
        iter = self.model.current_iter
        if iter: self.model.row_changed(self.model.get_path(iter), iter)

    def set_all_column_headers(cls, headers):
        try: headers.remove("~current")
        except ValueError: pass
        cls.headers = headers
        for listview in cls.__songlistviews:
            listview.set_column_headers(headers)

        star = list(Query.STAR)
        for header in headers:
            if not header.startswith("~#") and header not in star:
                star.append(header)
        SongList.star = star

    set_all_column_headers = classmethod(set_all_column_headers)

    def get_sort_by(self):
        for header in self.get_columns():
            if header.get_sort_indicator():
                return (header.header_name,
                        header.get_sort_order() == gtk.SORT_DESCENDING)
        else: return "artist", False

    # Resort based on the header clicked.
    def set_sort_by(self, header, tag=None, order=None, refresh=True):
        if header and tag is None: tag = header.header_name

        for h in self.get_columns():
            if h.header_name == tag:
                if order is None:
                    s = header.get_sort_order()
                    if (not header.get_sort_indicator() or
                        s == gtk.SORT_DESCENDING):
                        s = gtk.SORT_ASCENDING
                    else: s = gtk.SORT_DESCENDING
                else:
                    if order: s = gtk.SORT_DESCENDING
                    else: s = gtk.SORT_ASCENDING
                h.set_sort_indicator(True)
                h.set_sort_order(s)
            else: h.set_sort_indicator(False)
        if refresh: self.set_songs(self.get_songs())

    def set_model(self, model):
        super(SongList, self).set_model(model)
        if model is not None: model.connect('songs-set', self.__songs_set)
        self.model = model

    def get_songs(self):
        try: return self.get_model().get()
        except AttributeError: return [] # model is None

    def set_songs(self, songs, sorted=False):
        model = self.get_model()

        if not sorted:
            tag, reverse = self.get_sort_by()
            if tag == "~#track": tag = "album"
            elif tag == "~#disc": tag = "album"
            elif tag == "~length": tag = "~#length"
            elif tag == "~album~part": tag = "album"

            songs = [(song(tag), song.sort_key, song) for song in songs]
            songs.sort()
            if reverse: songs.reverse()
            songs = [song[2] for song in songs]
        else:
            self.set_sort_by(None, refresh=False)

        for column in self.get_columns():
            column.set_clickable(False)
            column.set_reorderable(False)

        if self.window:
            self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))

        model.set(songs)

    def __songs_set(self, songlist):
        for column in self.get_columns():
            if column.header_name not in["~current"]:
                column.set_clickable(True)
                column.set_reorderable(True)
        if self.window: self.window.set_cursor(None)

    def get_selected_songs(self):
        model, rows = self.get_selection().get_selected_rows()
        return [model[row][0] for row in rows]

    def __song_updated(self, watcher, songs):
        model = self.get_model()
        for row in model:
            if row[0] in songs: model.row_changed(row.path, row.iter)

    def __song_removed(self, watcher, songs):
        # The selected songs are removed from the library and should
        # be removed from the view.
        map(self.model.remove, self.model.find_all(songs))

    def __song_properties(self, watcher):
        model, rows = self.get_selection().get_selected_rows()
        if rows: songs = [model[row][0] for row in rows]
        else:
            from player import playlist
            songs = [playlist.song]
        SongProperties(watcher, songs)

    # Build a new filter around our list model, set the headers to their
    # new values.
    def set_column_headers(self, headers):
        if len(headers) == 0: return
        map(self.remove_column, self.get_columns())

        if self.CurrentColumn is not None:
            self.append_column(self.CurrentColumn())

        for i, t in enumerate(headers):
            if t in ["tracknumber", "discnumber"]:
                column = self.TextColumn(t)
            elif t in ["~#added", "~#mtime", "~#lastplayed", "~#laststarted"]:
                column = self.DateColumn(t)
            elif t in ["~length", "~#length"]: column = self.LengthColumn()
            elif t in ["~rating", "~#rating"]: column = self.RatingColumn()
            elif t.startswith("~#"): column = self.NumericColumn(t)
            elif t in ["~filename", "~basename", "~dirname"]:
                column = self.FSColumn(t)
            elif "~" not in t and t != "title":
                column = self.NonSynthTextColumn(t)
            elif t.startswith("<"):
                column = self.PatternColumn(t)
            else: column = self.WideTextColumn(t)
            column.connect('clicked', self.set_sort_by)
            column.set_reorderable(True)
            self.append_column(column)

    def __destroy(self):
        del(self.__songlistviews[self])
        self.set_model(None)
