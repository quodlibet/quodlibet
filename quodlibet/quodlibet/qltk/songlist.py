# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import datetime
import time

import gobject
import gtk
import pango

from quodlibet import config
from quodlibet import const
from quodlibet import player
from quodlibet import qltk
from quodlibet import util

from quodlibet.parse import Query, Pattern
from quodlibet.qltk.information import Information
from quodlibet.qltk.properties import SongProperties
from quodlibet.qltk.views import AllTreeView
from quodlibet.qltk.ratingsmenu import RatingsMenuItem
from quodlibet.util.uri import URI
from quodlibet.qltk.playorder import ORDERS
from quodlibet.formats._audio import TAG_TO_SORT, FILESYSTEM_TAGS, AudioFile
from quodlibet.qltk.sortdialog import SortDialog
from quodlibet.util import human_sort_key

class PlaylistMux(object):

    def __init__(self, player, q, pl):
        self.q = q
        self.pl = pl
        player.connect('song-started', self.__check_q)

    def __check_q(self, player, song):
        if song is not None:
            iter = self.q.find(song)
            if iter: self.q.remove(iter)
            self.q.reset()

    def get_current(self):
        if self.q.current is not None: return self.q.current
        else: return self.pl.current

    current = property(get_current)

    def next(self):
        if self.q.is_empty():
            self.pl.next()
            self.q.sourced = False
            self.pl.sourced = True
        elif self.q.current is None:
            self.q.next()
            self.q.sourced = True
            self.pl.sourced = False

    def next_ended(self):
        if self.q.is_empty():
            self.pl.next_ended()
            self.q.sourced = False
            self.pl.sourced = True
        elif self.q.current is None:
            self.q.next()
            self.q.sourced = True
            self.pl.sourced = False

    def previous(self):
        self.pl.previous()

    def go_to(self, song, explicit=False):
        print_d("Told to go to %r" % song, context=self)
        self.q.go_to(None)
        return self.pl.go_to(song, explicit)

    def reset(self):
        self.pl.reset()
        self.q.go_to(None)
        if not self.pl.is_empty():
            self.next()

    def enqueue(self, songs):
        for song in songs:
            self.q.append(row=[song])

    def unqueue(self, songs):
        map(self.q.remove, filter(None, map(self.q.find, songs)))

class PlaylistModel(gtk.ListStore):
    order = None
    repeat = False
    sourced = False
    __iter = None
    __old_value = None

    __gsignals__ = {
        'songs-set': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ())
        }

    def __init__(self):
        super(PlaylistModel, self).__init__(object)
        self.order = ORDERS[0](self)

        # The playorder plugins use paths atm to remember songs so
        # we need to reset them if the paths change somehow.
        self.__sigs = []
        for sig in ['row-deleted', 'row-inserted', 'rows-reordered']:
            s = self.connect(sig, lambda pl, *x: self.order.reset(pl))
            self.__sigs.append(s)

    def set(self, songs):
        oldsong = self.current
        if oldsong is None: oldsong = self.__old_value
        else: self.__old_value = oldsong
        self.order.reset(self)
        self.__iter = None

        # We just reset the order manually so block the signals
        map(self.handler_block, self.__sigs)
        print_d("Clearing model.", context=self)
        self.clear()
        print_d("Setting %d songs." % len(songs), context=self)
        insert = self.insert
        for song in reversed(songs):
            iter = insert(0, (song,))
            if song is oldsong:
                self.__iter = iter
        if self.__iter is not None:
            self.__old_value = None
        print_d("Done filling model.", context=self)
        map(self.handler_unblock, self.__sigs)
        self.emit('songs-set')

    def reverse(self):
        if not len(self): return
        self.order.reset(self)
        map(self.handler_block, self.__sigs)
        self.reorder(range(len(self)-1, -1, -1))
        map(self.handler_unblock, self.__sigs)

    def remove(self, iter):
        if self.__iter and self[iter].path == self[self.__iter].path:
            self.__iter = None
        super(PlaylistModel, self).remove(iter)

    def get(self):
        return [row[0] for row in self]

    def get_current(self):
        if self.__iter is None: return None
        elif self.is_empty(): return None
        else: return self[self.__iter][0]

    current = property(get_current)

    def get_current_path(self):
        if self.__iter is None: return None
        elif self.is_empty(): return None
        else: return self[self.__iter].path
    current_path = property(get_current_path)

    def get_current_iter(self):
        if self.__iter is None: return None
        elif self.is_empty(): return None
        else: return self.__iter
    current_iter = property(get_current_iter)

    def next(self):
        self.__iter = self.order.next_explicit(self, self.__iter)

    def next_ended(self):
        self.__iter = self.order.next_implicit(self, self.__iter)

    def previous(self):
        self.__iter = self.order.previous_explicit(self, self.__iter)

    def go_to(self, song, explicit=False):
        print_d("Told to go to %r" % song, context=self)
        self.__iter = None
        if isinstance(song, gtk.TreeIter):
            self.__iter = song
            self.sourced = True
        else:
            for row in self:
                if row[0] == song:
                    self.__iter = row.iter
                    print_d("Found song at %r" % row, context=self)
                    self.sourced = True
                    break
            else:
                print_d("Failed to find song", context=self)
        if explicit:
            self.__iter = self.order.set_explicit(self, self.__iter)
        else:
            self.__iter = self.order.set_implicit(self, self.__iter)
        return self.__iter

    def find(self, song):
        for row in self:
            if row[0] == song: return row.iter
        return None

    def find_all(self, songs):
        return [row.iter for row in self if row[0] in songs]

    def __contains__(self, song):
        return bool(self.find(song))

    def is_empty(self):
        return not len(self)

    def reset(self):
        self.go_to(None)
        self.order.reset(self)

class SongList(AllTreeView, util.InstanceTracker):
    # A TreeView containing a list of songs.

    headers = [] # The list of current headers.
    star = list(Query.STAR)

    CurrentColumn = None

    class TextColumn(qltk.views.TreeViewColumnButton):
        # Base class for other kinds of columns.
        _label = gtk.Label().create_pango_layout("")
        __last_rendered = None

        def _needs_update(self, value):
            if self.__last_rendered == value:
                return False
            self.__last_rendered = value
            return True

        def _cdf(self, column, cell, model, iter, tag):
            text = model[iter][0].comma(tag)
            if not self._needs_update(text): return
            cell.set_property('text', text)
            self._update_layout(text, cell)

        def _delayed_update(self):
            max_width = -1
            width = self.get_fixed_width()
            for text, pad, cell_pad in self._text:
                self._label.set_text(text)
                new_width = self._label.get_pixel_size()[0] + pad +  cell_pad
                if new_width > max_width:
                    max_width = new_width
            if width < max_width:
                self.set_fixed_width(max_width)
                tv = self.get_tree_view()
                if tv: tv.columns_autosize()
            self._text.clear()
            self._timeout = None
            return False

        def _update_layout(self, text, cell=None, pad=12, force=False):
            if not self.get_resizable():
                cell_pad = (cell and cell.get_property('xpad')) or 0
                self._text.add((text, pad, cell_pad))
                if force: self._delayed_update()
                if self._timeout is not None:
                    gobject.source_remove(self._timeout)
                    self._timeout = None
                self._timeout = gobject.idle_add(self._delayed_update,
                    priority=gobject.PRIORITY_LOW)

        def __init__(self, t):
            self._render = gtk.CellRendererText()
            title = util.tag(t)
            super(SongList.TextColumn, self).__init__(title, self._render)
            self.header_name = t
            self.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            self.set_visible(True)
            self.set_clickable(True)
            self.set_sort_indicator(False)
            self.set_cell_data_func(self._render, self._cdf, t)
            self._text = set()
            self._timeout = None
            self._update_layout(title, force=True)

    class DateColumn(TextColumn):
        # The '~#' keys that are dates.
        def _cdf(self, column, cell, model, iter, tag):
            stamp = model[iter][0](tag)
            if not self._needs_update(stamp): return
            if not stamp:
                cell.set_property('text', _("Never"))
            else:
                date = datetime.datetime.fromtimestamp(stamp).date()
                today = datetime.datetime.now().date()
                days = (today - date).days
                if days == 0: format = "%X"
                elif days < 7: format = "%A"
                else: format = "%x"
                stamp = time.localtime(stamp)
                text = time.strftime(format, stamp).decode(const.ENCODING)
                cell.set_property('text', text)
            self._update_layout(cell.get_property('text'), cell)

    class WideTextColumn(TextColumn):
        # Resizable and ellipsized at the end. Used for any key with
        # a '~' in it, and 'title'.
        def __init__(self, tag):
            super(SongList.WideTextColumn, self).__init__(tag)
            self._render.set_property('ellipsize', pango.ELLIPSIZE_END)
            self.set_expand(True)
            self.set_resizable(True)
            self.set_fixed_width(1)

    class RatingColumn(TextColumn):
        # Render ~#rating directly (simplifies filtering, saves
        # a function call).
        def _cdf(self, column, cell, model, iter, tag):
                value = model[iter][0].get("~#rating", const.DEFAULT_RATING)
                if not self._needs_update(value): return
                cell.set_property('text', util.format_rating(value))
                # No need to update layout, we know this width at
                # at startup.

        def __init__(self):
            super(SongList.RatingColumn, self).__init__("~#rating")
            self._update_layout(util.format_rating(1.0))
            self.set_resizable(False)
            self.set_expand(False)

    class NonSynthTextColumn(WideTextColumn):
        # Optimize for non-synthesized keys by grabbing them directly.
        # Used for any tag without a '~' except 'title'.
        def _cdf(self, column, cell, model, iter, tag):
            value = model[iter][0].get(tag, "")
            if not self._needs_update(value): return
            cell.set_property('text', value.replace("\n", ", "))

    class FSColumn(WideTextColumn):
        # Contains text in the filesystem encoding, so needs to be
        # decoded safely (and also more slowly).
        def _cdf(self, column, cell, model, iter, tag):
            value = model[iter][0].comma(tag)
            if not self._needs_update(value): return
            cell.set_property('text', util.unexpand(util.fsdecode(value)))

    class NumericColumn(TextColumn):
        # Any '~#' keys except dates.
        def _cdf(self, column, cell, model, iter, tag):
            value = model[iter][0].comma(tag)
            if not self._needs_update(value): return
            text = unicode(value)
            cell.set_property('text', text)
            self._update_layout(text, cell)

        def __init__(self, tag):
            super(SongList.NumericColumn, self).__init__(tag)
            self._render.set_property('xalign', 1.0)
            self.set_alignment(1.0)

    class LengthColumn(NumericColumn):
        def _cdf(self, column, cell, model, iter, tag):
            value = model[iter][0].get("~#length", 0)
            if not self._needs_update(value): return
            text = util.format_time(value)
            cell.set_property('text', text)
            self._update_layout(text, cell)
        def __init__(self):
            super(SongList.LengthColumn, self).__init__("~#length")

    class FilesizeColumn(NumericColumn):
        def _cdf(self, column, cell, model, iter, tag):
            value = model[iter][0].get("~#filesize", 0)
            if not self._needs_update(value): return
            text = util.format_size(value)
            cell.set_property('text', text)
            self._update_layout(text, cell)
        def __init__(self):
            super(SongList.FilesizeColumn, self).__init__("~#filesize")

    class PatternColumn(WideTextColumn):
        def _cdf(self, column, cell, model, iter, tag):
            song = model.get_value(iter, 0)
            value = self._pattern % song
            if not self._needs_update(value): return
            cell.set_property('text', value)

        def __init__(self, pattern):
            super(SongList.PatternColumn, self).__init__(util.pattern(pattern))
            self.header_name = pattern
            self._pattern = Pattern(pattern)

    def Menu(self, header, browser, library):
        songs = self.get_selected_songs()
        if not songs: return

        can_filter = browser.can_filter

        menu = browser.Menu(songs, self, library)

        def Filter(t):
            # Translators: The substituted string is the name of the
            # selected column (a translated tag name).
            b = qltk.MenuItem(
                _("_Filter on %s") % util.tag(t, True), gtk.STOCK_INDEX)
            b.connect_object('activate', self.__filter_on, t, songs, browser)
            return b

        header = util.tagsplit(header)[0]

        if can_filter("album") or can_filter("artist") or can_filter(header):
            menu.preseparate()

        if can_filter("artist"): menu.prepend(Filter("artist"))
        if can_filter("album"): menu.prepend(Filter("album"))
        if (header not in ["artist", "album"] and can_filter(header)):
            menu.prepend(Filter(header))

        ratings = RatingsMenuItem(songs, library)
        menu.preseparate()
        menu.prepend(ratings)
        menu.show_all()
        return menu

    def __init__(self, library, player=None):
        super(SongList, self).__init__()
        self._register_instance(SongList)
        self.set_model(PlaylistModel())
        self.set_size_request(200, 150)
        self.set_rules_hint(True)
        self.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.set_fixed_height_mode(True)
        self.__csig = self.connect('columns-changed', self.__columns_changed)
        self.set_column_headers(self.headers)
        librarian = library.librarian or library
        sigs = []
        # The player needs to be called first so it can ge the next song
        # in case the current one gets deleted and the order gets reset.
        if player:
            s = librarian.connect_object('removed', map, player.remove)
            sigs.append(s)
        sigs.extend([librarian.connect('changed', self.__song_updated),
                librarian.connect('removed', self.__song_removed)])
        for sig in sigs:
            self.connect_object('destroy', librarian.disconnect, sig)
        if player:
            sigs = [player.connect('paused', self.__redraw_current),
                    player.connect('unpaused', self.__redraw_current)]
            for sig in sigs:
                self.connect_object('destroy', player.disconnect, sig)

        self.connect('button-press-event', self.__button_press, librarian)
        self.connect('key-press-event', self.__key_press, librarian)

        self.disable_drop()
        self.connect('drag-motion', self.__drag_motion)
        self.connect('drag-leave', self.__drag_leave)
        self.connect('drag-data-get', self.__drag_data_get)
        self.connect('drag-data-received', self.__drag_data_received, library)

        self.set_search_equal_func(self.__search_func)

        self.accelerators = gtk.AccelGroup()
        key, mod = gtk.accelerator_parse("<alt>Return")
        self.accelerators.connect_group(
            key, mod, 0, lambda *args: self.__song_properties(librarian))
        key, mod = gtk.accelerator_parse("<control>I")
        self.accelerators.connect_group(
            key, mod, 0, lambda *args: self.__information(librarian))

        self.connect('destroy', self.__destroy)

        self.__scroll_delay = None
        self.__scroll_periodic = None
        self.__scroll_args = (0, 0, 0, 0)
        self.__scroll_length = 0
        self.__scroll_last = None

        # If the a song changes, we can't simply reverse the model
        # (same tag, changed song order)
        self.__sort_dirty = False

    def __destroy(self, *args):
        self.handler_block(self.__csig)
        map(self.remove_column, self.get_columns())
        self.handler_unblock(self.__csig)

    def __search_func(self, model, column, key, iter, *args):
        for column in self.get_columns():
            value = model.get_value(iter, 0)(column.header_name)
            if not isinstance(value, basestring): continue
            elif key in value.lower() or key in value: return False
        else: return True

    def enable_drop(self, by_row=True):
        targets = [("text/x-quodlibet-songs", gtk.TARGET_SAME_APP, 1),
                   ("text/uri-list", 0, 2)]
        self.drag_source_set(
            gtk.gdk.BUTTON1_MASK, targets,
            gtk.gdk.ACTION_COPY|gtk.gdk.ACTION_MOVE)
        self.drag_dest_set(gtk.DEST_DEFAULT_ALL, targets,
                           gtk.gdk.ACTION_COPY|gtk.gdk.ACTION_MOVE)
        self.__drop_by_row = by_row

    def disable_drop(self):
        targets = [("text/x-quodlibet-songs", gtk.TARGET_SAME_APP, 1),
                   ("text/uri-list", 0, 2)]
        self.drag_source_set(
            gtk.gdk.BUTTON1_MASK, targets, gtk.gdk.ACTION_COPY)
        self.drag_dest_unset()

    def __enable_scroll(self):
        """Start scrolling if it hasn't already"""
        if self.__scroll_periodic is not None or \
            self.__scroll_delay is not None:
            return

        def periodic_scroll():
            """Get the tree coords for 0,0 and scroll from there"""
            wx, wy, dist, ref = self.__scroll_args
            x, y = self.widget_to_tree_coords(0, 0)

            # We reached an end, stop
            if self.__scroll_last == y:
                self.__disable_scroll()
                return
            self.__scroll_last = y

            # If we went full speed for a while.. speed up
            # .. every number is made up here
            if self.__scroll_length >= 50 * ref:
                dist *= self.__scroll_length / (ref * 10)
            if self.__scroll_length < 2000 * ref:
                self.__scroll_length += abs(dist)

            self.scroll_to_point(-1, y + dist)
            self.__drag_set_dest(wx, wy)
            # we have to readd the timeout.. otherwise they could add up
            # because scroll can last longer than 50ms
            gobject.source_remove(self.__scroll_periodic)
            enable_periodic_scroll()

        def enable_periodic_scroll():
            self.__scroll_periodic = gobject.timeout_add(50, periodic_scroll)

        self.__scroll_delay = gobject.timeout_add(350, enable_periodic_scroll)

    def __disable_scroll(self):
        if self.__scroll_periodic is not None:
            gobject.source_remove(self.__scroll_periodic)
            self.__scroll_periodic = None
        if self.__scroll_delay is not None:
            gobject.source_remove(self.__scroll_delay)
            self.__scroll_delay = None
        self.__scroll_length = 0
        self.__scroll_last = None

    def __scroll_motion(self, x, y):
        # TODO: move it views so every treeview can use it
        visible_rect = self.get_visible_rect()
        if visible_rect is None:
            self.__disable_scroll()
            return

        # I guess the bin to visible_rect difference is the header height
        # but this could be wrong
        start = self.get_bin_window().get_geometry()[1] - 1
        end = visible_rect.height + start

        # Get the font height as size reference
        reference = self.create_pango_layout("").get_pixel_size()[1]

        # If the drag is in the scroll area, adjust the speed
        scroll_offset = int(reference * 3)
        in_upper_scroll = (start < y < start + scroll_offset)
        in_lower_scroll = (y > end - scroll_offset)

        # thanks TI200
        accel = lambda x: int(1.1**(x*12/reference)) - (x/reference)
        if in_lower_scroll:
            diff = accel(y - end + scroll_offset)
        elif in_upper_scroll:
            diff = - accel(start + scroll_offset - y)
        else:
            self.__disable_scroll()
            return

        # The area where we can go to full speed
        full_offset = int(reference * 0.8)
        in_upper_full = (start < y < start + full_offset)
        in_lower_full = (y > end - full_offset)
        if not in_upper_full and not in_lower_full:
            self.__scroll_length = 0

        # For the periodic scroll function
        self.__scroll_args = (x, y, diff, reference)

        # The area to trigger a scroll is a bit smaller
        trigger_offset = int(reference * 2.5)
        in_upper_trigger = (start < y < start + trigger_offset)
        in_lower_trigger = (y > end - trigger_offset)

        if in_upper_trigger or in_lower_trigger:
            self.__enable_scroll()

    def __drag_leave(self, widget, ctx, time):
        widget.parent.drag_unhighlight()
        self.__disable_scroll()

    def __drag_set_dest(self, x, y):
        try: self.set_drag_dest_row(*self.get_dest_row_at_pos(x, y))
        except TypeError:
            if len(self.get_model()) == 0: path = 0
            else: path = len(self.get_model()) - 1
            self.set_drag_dest_row(path, gtk.TREE_VIEW_DROP_AFTER)

    def __drag_motion(self, view, ctx, x, y, time):
        if self.__drop_by_row:
            self.__drag_set_dest(x, y)
            self.__scroll_motion(x, y)
            if ctx.get_source_widget() == self: kind = gtk.gdk.ACTION_MOVE
            else: kind = gtk.gdk.ACTION_COPY
            ctx.drag_status(kind, time)
            return True
        else:
            self.parent.drag_highlight()
            ctx.drag_status(gtk.gdk.ACTION_COPY, time)
            return True

    def __drag_data_delete(self, view, ctx):
        map(view.get_model(), self.__drag_iters)
        self.__drag_iters = []

    def __drag_data_get(self, view, ctx, sel, tid, etime):
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
            filenames = [song("~filename") for song in songs]
            sel.set("text/x-quodlibet-songs", 8, "\x00".join(filenames))
            if ctx.action == gtk.gdk.ACTION_MOVE:
                self.__drag_iters = map(model.get_iter, paths)
            else: self.__drag_iters = []
        else:
            uris = [model[path][0]("~uri") for path in paths]
            sel.set_uris(uris)
            self.__drag_iters = []

    def __drag_data_browser_dropped(self, songs):
        window = qltk.get_top_parent(self)
        if callable(window.browser.dropped):
            return window.browser.dropped(self, songs)
        else: return False

    def __drag_data_received(self, view, ctx, x, y, sel, info, etime, library):
        model = view.get_model()
        if info == 1:
            filenames = sel.data.split("\x00")
            move = (ctx.get_source_widget() == view)
        elif info == 2:
            def to_filename(s):
                try: return URI(s).filename
                except ValueError: return None

            filenames = map(to_filename, sel.get_uris())
            move = False
        else:
            ctx.finish(False, False, etime)
            return

        to_add = []
        for filename in filenames:
            if filename not in library.librarian:
                library.add_filename(filename)
            elif filename not in library:
                to_add.append(library.librarian[filename])
        library.add(to_add)
        songs = filter(None, map(library.get, filenames))
        if not songs:
            ctx.finish(bool(not filenames), False, etime)
            return

        if not self.__drop_by_row:
            success = self.__drag_data_browser_dropped(songs)
            ctx.finish(success, False, etime)
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

    def __custom_sort(self, *args):
        sd = SortDialog(qltk.get_top_parent(self))
        if sd.run() == gtk.RESPONSE_OK:
            # sort_keys yields a list of pairs (sort header, order)
            headers = sd.sort_keys()
            if not headers:
                return
            # from this, we have to construct a comparison function for sort
            def _get_key(song, tag):
                if tag.startswith("~#") and "~" not in tag[2:]:
                    return song(tag)
                return human_sort_key(song(tag))
            def comparer(x, y):
                for (h, o) in headers:
                    c = cmp(_get_key(x, h), _get_key(y, h))
                    if c == 0: continue
                    if o != gtk.SORT_ASCENDING:
                        c *= -1
                    return c
                return 0
            songs = self.get_songs()
            songs.sort(cmp=comparer)
            self.set_songs(songs, sorted=True)
        sd.hide()

    def __button_press(self, view, event, librarian):
        if event.button != 1: return
        x, y = map(int, [event.x, event.y])
        try: path, col, cellx, celly = view.get_path_at_pos(x, y)
        except TypeError: return True
        if event.window != self.get_bin_window(): return False
        if col.header_name == "~#rating":
            if not config.getboolean("browsers", "rating_click"): return

            song = view.get_model()[path][0]
            l = gtk.Label()
            l.set_text(util.format_rating(util.RATING_PRECISION))
            width = l.size_request()[0]
            l.destroy()
            count = int(float(cellx - 5) / width) + 1
            rating = max(0.0, min(1.0, count * util.RATING_PRECISION))
            if (rating <= util.RATING_PRECISION and
                song("~#rating") == util.RATING_PRECISION): rating = 0
            self.__set_rating(rating, [song], librarian)

    def __set_rating(self, value, songs, librarian):
        count = len(songs)
        if (count > 1 and
            config.getboolean("browsers", "rating_confirm_multiple")):
            if not qltk.ConfirmAction(
                self, _("Confirm rating"),
                _("You are about to change the rating of %d songs.\n"
                  "Do you wish to continue?") % count).run():
                return;
        for song in songs:
            song["~#rating"] = value
        librarian.changed(songs)

    def __key_press(self, songlist, event, librarian):
        if event.string in ['0', '1', '2', '3', '4']:
            rating = min(1.0, int(event.string) * util.RATING_PRECISION)
            self.__set_rating(rating, self.get_selected_songs(), librarian)
            return True
        elif qltk.is_accel(event, "<ctrl>Return") or \
            qltk.is_accel(event, "<ctrl>KP_Enter"):
            self.__enqueue(self.get_selected_songs())
            return True
        elif qltk.is_accel(event, "<control>F"):
            self.emit('start-interactive-search')
            return True
        return False

    def __enqueue(self, songs):
        songs = filter(lambda s: s.can_add, songs)
        if songs:
            from quodlibet.widgets import main
            main.playlist.enqueue(songs)

    def __redraw_current(self, player, song=None):
        iter = self.model.current_iter
        if iter: self.model.row_changed(self.model.get_path(iter), iter)

    def __columns_changed(self, *args):
        headers = map(lambda h: h.header_name, self.get_columns())
        SongList.set_all_column_headers(headers)
        SongList.headers = headers

    def set_all_column_headers(cls, headers):
        config.set("settings", "headers", " ".join(headers))
        try: headers.remove("~current")
        except ValueError: pass
        cls.headers = headers
        for listview in cls.instances():
            listview.set_column_headers(headers)

        star = list(Query.STAR)
        for header in headers:
            if "<" in header:
                tags = Pattern(header).tags
            else:
                tags = util.tagsplit(header)
            for tag in tags:
                if not tag.startswith("~#") and tag not in star:
                    star.append(tag)
        SongList.star = star

    set_all_column_headers = classmethod(set_all_column_headers)

    def get_sort_by(self):
        for header in self.get_columns():
            if header.get_sort_indicator():
                tag = header.header_name
                sort = header.get_sort_order()
                return (tag, sort == gtk.SORT_DESCENDING)
        else: return "album", False

    def is_sorted(self):
        return max([c.get_sort_indicator() for c in self.get_columns()] or [0])

    # Resort based on the header clicked.
    def set_sort_by(self, header, tag=None, order=None, refresh=True):
        if header and tag is None: tag = header.header_name

        rev = False
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
                rev = h.get_sort_indicator()
                h.set_sort_indicator(True)
                h.set_sort_order(s)
            else: h.set_sort_indicator(False)
        if refresh:
            if rev:
                if self.__sort_dirty:
                    # python sort is faster if it's presorted.
                    songs = self.get_songs()
                    songs.reverse()
                    self.set_songs(songs)
                else:
                    self.reverse()
            else: self.set_songs(self.get_songs())

    def set_model(self, model):
        super(SongList, self).set_model(model)
        self.model = model
        self.set_search_column(0)

    def get_songs(self):
        try: return self.get_model().get()
        except AttributeError: return [] # model is None

    def __get_sort_tag(self, tag):
        replace_order = {
            "~#track": "album",
            "~#disc": "album",
            "~length": "~#length"
        }

        if tag == "~title~version":
            tag = "title"
        elif tag == "~album~discsubtitle":
            tag = "album"

        if tag.startswith("<"):
            for key, value in replace_order.iteritems():
                tag = tag.replace("<%s>" % key, "<%s>" % value)
            tag = Pattern(tag).format
        else:
            tags = util.tagsplit(tag)
            sort_tags = []
            for tag in tags:
                tag = replace_order.get(tag, tag)
                tag = TAG_TO_SORT.get(tag, tag)
                if tag not in sort_tags:
                    sort_tags.append(tag)
            if len(sort_tags) > 1:
                tag = "~" + "~".join(sort_tags)

        return tag

    def set_songs(self, songs, sorted=False):
        model = self.get_model()
        self.__sort_dirty = False

        if not sorted:
            tag, reverse = self.get_sort_by()
            tag = self.__get_sort_tag(tag)

            #try to set a sort indicator that matches the default order
            if not self.is_sorted():
                for h in self.get_columns():
                    name = h.header_name
                    if self.__get_sort_tag(name) == tag:
                        h.set_sort_indicator(True)
                        h.set_sort_order(gtk.SORT_ASCENDING)
                        break

            sort_func = AudioFile.sort_by_func(tag)
            songs.sort(key=sort_func, reverse=reverse)
        else:
            self.set_sort_by(None, refresh=False)

        # Doing set_model(None) resets the sort indicator, so we need to
        # remember it before doing that.
        sorts = map(gtk.TreeViewColumn.get_sort_indicator, self.get_columns())
        print_d("Detaching model.", context=self)
        self.set_model(None)
        model.set(songs)
        print_d("Attaching model.", context=self)
        self.set_model(model)
        print_d("Model attached.", context=self)
        map(gtk.TreeViewColumn.set_sort_indicator, self.get_columns(), sorts)

    def reverse(self):
        model = self.get_model()
        sorts = map(gtk.TreeViewColumn.get_sort_indicator, self.get_columns())
        self.set_model(None)
        model.reverse()
        self.set_model(model)
        map(gtk.TreeViewColumn.set_sort_indicator, self.get_columns(), sorts)

    def get_selected_songs(self):
        selection = self.get_selection()
        if selection is None: return []
        model, rows = selection.get_selected_rows()
        return [model[row][0] for row in rows]

    def __song_updated(self, librarian, songs):
        """Only update rows that are currently displayed.
        Warning: This makes the row-changed signal useless."""
        self.__sort_dirty = True
        #pygtk 2.12: prevent invalid ranges or GTK asserts
        if not self.flags() & gtk.REALIZED or \
            self.get_path_at_pos(0,0) is None: return
        vrange = self.get_visible_range()
        if vrange is None: return
        (start,), (end,) = vrange
        model = self.get_model()
        for path in xrange(start, end+1):
            row = model[path]
            if row[0] in songs:
                model.row_changed(row.path, row.iter)

    def __song_removed(self, librarian, songs):
        # The selected songs are removed from the library and should
        # be removed from the view.

        if not len(self.model):
            return

        songs = set(songs)

        # search in the selection first
        # speeds up common case: select songs and remove them
        model, rows = self.get_selection().get_selected_rows()
        rows = rows or []
        iters = [model[r].iter for r in rows if model[r][0] in songs]

        # if not all songs were in the selection, search the whole view
        if len(iters) != len(songs):
            iters = model.find_all(songs)

        selection_removed = (len(iters) == len(rows))
        self._remove(iters, set_selection=selection_removed)

    def _remove(self, iters, set_selection=True):
        """Removes the rows from the model and selects the row
        after the last removed one if specified."""

        model = self.model
        map(model.remove, iters)

        if not set_selection: return

        # model.remove makes the removed iter point to the next row if possible
        # so check if the last iter is a valid one and select it or
        # simply select the last row
        selection = self.get_selection()
        if len(iters) and model.iter_is_valid(iters[-1]):
            selection.select_iter(iters[-1])
        elif len(model):
            selection.select_path(model[-1].path)

    def __song_properties(self, librarian):
        model, rows = self.get_selection().get_selected_rows()
        if rows:
            songs = [model[row][0] for row in rows]
        else:
            from quodlibet.player import playlist
            if playlist.song:
                songs = [playlist.song]
            else: return
        SongProperties(librarian, songs, parent=self)

    def __information(self, librarian):
        model, rows = self.get_selection().get_selected_rows()
        if rows:
            songs = [model[row][0] for row in rows]
        else:
            from quodlibet.player import playlist
            if playlist.song:
                songs = [playlist.song]
            else: return
        Information(librarian, songs, self)

    # Build a new filter around our list model, set the headers to their
    # new values.
    def set_column_headers(self, headers):
        if len(headers) == 0: return

        self.handler_block(self.__csig)

        old_sort = self.is_sorted() and self.get_sort_by()
        map(self.remove_column, self.get_columns())

        if self.CurrentColumn is not None:
            self.append_column(self.CurrentColumn())

        for i, t in enumerate(headers):
            if t in ["tracknumber", "discnumber"]:
                column = self.TextColumn(t)
            elif t in ["~#added", "~#mtime", "~#lastplayed", "~#laststarted"]:
                column = self.DateColumn(t)
            elif t in ["~length", "~#length"]: column = self.LengthColumn()
            elif t == "~#filesize": column = self.FilesizeColumn()
            elif t in ["~rating", "~#rating"]: column = self.RatingColumn()
            elif t.startswith("~#"): column = self.NumericColumn(t)
            elif t in FILESYSTEM_TAGS:
                column = self.FSColumn(t)
            elif t.startswith("<"):
                column = self.PatternColumn(t)
            elif "~" not in t and t != "title":
                column = self.NonSynthTextColumn(t)
            else: column = self.WideTextColumn(t)
            column.connect('clicked', self.set_sort_by)
            column.connect('button-press-event', self.__showmenu)
            column.connect('popup-menu', self.__showmenu)
            column.set_reorderable(True)
            self.append_column(column)

        if old_sort:
            header, order = old_sort
            self.set_sort_by(None, header, order, False)

        self.handler_unblock(self.__csig)

    def __getmenu(self, column):
        menu = gtk.Menu()
        menu.connect_object('selection-done', gtk.Menu.destroy, menu)

        current = SongList.headers[:]
        current_set = set(current)
        def tag_title(tag):
            if tag.startswith("<"):
                return util.pattern(tag)
            return util.tag(tag)
        current = zip(map(tag_title, current), current)

        def add_header_toggle(menu, (header, tag), active, column=column):
            item = gtk.CheckMenuItem(header)
            item.tag = tag
            item.set_active(active)
            item.connect('activate', self.__toggle_header_item, column)
            item.show()
            item.set_tooltip_text(tag)
            menu.append(item)

        for header in current:
            add_header_toggle(menu, header, True)

        sep = gtk.SeparatorMenuItem()
        sep.show()
        menu.append(sep)

        trackinfo = """title genre ~title~version ~#track
            ~#playcount ~#skipcount ~#rating ~#length""".split()
        peopleinfo = """artist ~people performer arranger author composer
            conductor lyricist originalartist""".split()
        albuminfo = """album ~album~discsubtitle labelid ~#disc ~#discs
            ~#tracks albumartist""".split()
        dateinfo = """date originaldate recordingdate ~#laststarted
            ~#lastplayed ~#added ~#mtime""".split()
        fileinfo = """~format ~#bitrate ~#filesize ~filename ~basename ~dirname
            ~uri""".split()
        copyinfo = """copyright organization location isrc
            contact website""".split()
        all_headers = reduce(lambda x,y: x+y,
            [trackinfo, peopleinfo, albuminfo, dateinfo, fileinfo, copyinfo])

        for name, group in [
            (_("All _Headers"), all_headers),
            (_("_Track Headers"), trackinfo),
            (_("_Album Headers"), albuminfo),
            (_("_People Headers"), peopleinfo),
            (_("_Date Headers"), dateinfo),
            (_("_File Headers"), fileinfo),
            (_("_Production Headers"), copyinfo),
        ]:
            item = gtk.MenuItem(name)
            item.show()
            menu.append(item)
            submenu = gtk.Menu()
            item.set_submenu(submenu)
            for header in sorted(zip(map(util.tag, group), group)):
                add_header_toggle(submenu, header, header[1] in current_set)

        sep = gtk.SeparatorMenuItem()
        sep.show()
        menu.append(sep)

        b = gtk.MenuItem(_("Custom _Sort..."))
        menu.append(b)
        b.show()
        b.connect('activate', self.__custom_sort)

        custom = gtk.MenuItem(_("_Customize Headers..."))
        custom.show()
        custom.connect('activate', self.__add_custom_column)
        menu.append(custom)

        return menu

    def __toggle_header_item(self, item, column):
        headers = SongList.headers[:]
        if item.get_active():
            try: headers.insert(self.get_columns().index(column), item.tag)
            except ValueError: headers.append(item.tag)
        else:
            try: headers.remove(item.tag)
            except ValueError: pass

        SongList.set_all_column_headers(headers)
        SongList.headers = headers

    def __add_custom_column(self, item):
        # Prefs has to import SongList, so do this here to avoid
        # a circular import.
        from quodlibet.qltk.prefs import PreferencesWindow
        PreferencesWindow(self).set_page("songlist")

    def __showmenu(self, column, event=None):
        time = gtk.get_current_event_time()
        if event is not None and event.button != 3:
            return

        if event:
            self.__getmenu(column).popup(None, None, None, event.button, time)
            return True

        widget = column.get_widget()
        return qltk.popup_menu_under_widget(self.__getmenu(column),
                widget, 3, time)
