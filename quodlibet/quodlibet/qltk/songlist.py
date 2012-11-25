# Copyright 2005 Joe Wreschnig
#           2012 Christoph Reiter
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
from quodlibet.qltk.views import AllTreeView, DragScroll
from quodlibet.qltk.ratingsmenu import RatingsMenuItem
from quodlibet.qltk.ratingsmenu import ConfirmRateMultipleDialog
from quodlibet.qltk.songmodel import PlaylistModel
from quodlibet.util.uri import URI
from quodlibet.formats._audio import TAG_TO_SORT, FILESYSTEM_TAGS, AudioFile
from quodlibet.qltk.sortdialog import SortDialog
from quodlibet.util import human_sort_key


class SongList(AllTreeView, DragScroll, util.InstanceTracker):
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
            if not self._pattern:
                return
            value = self._pattern % song
            if not self._needs_update(value): return
            cell.set_property('text', value)

        def __init__(self, pattern):
            super(SongList.PatternColumn, self).__init__(util.pattern(pattern))
            self.header_name = pattern
            self._pattern = None
            try: self._pattern = Pattern(pattern)
            except ValueError: pass

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

        if can_filter("artist") or can_filter("album") or can_filter(header):
            menu.preseparate()

        if can_filter("artist"):
            menu.prepend(Filter("artist"))
        if can_filter("album"):
            menu.prepend(Filter("album"))
        if (header not in ["artist", "album"] and can_filter(header)):
            menu.prepend(Filter(header))

        ratings = RatingsMenuItem(songs, library)
        menu.preseparate()
        menu.prepend(ratings)
        menu.show_all()
        return menu

    def __init__(self, library, player=None, update=False):
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
        if update:
            sigs.append(librarian.connect('added', self.__song_added))
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

    def __drag_leave(self, widget, ctx, time):
        widget.parent.drag_unhighlight()
        self.scroll_disable()

    def __drag_motion(self, view, ctx, x, y, time):
        if self.__drop_by_row:
            self.set_drag_dest(x, y)
            self.scroll_motion(x, y)
            if ctx.get_source_widget() == self: kind = gtk.gdk.ACTION_MOVE
            else: kind = gtk.gdk.ACTION_COPY
            ctx.drag_status(kind, time)
            return True
        else:
            self.parent.drag_highlight()
            ctx.drag_status(gtk.gdk.ACTION_COPY, time)
            return True

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

            filenames = filter(None, map(to_filename, sel.get_uris()))
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
        if not browser:
            return

        # Fall back to the playing song
        if songs is None:
            if player.playlist.song:
                songs = [player.song]
            else:
                return

        browser.filter_on(songs, header)

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
            dialog = ConfirmRateMultipleDialog(self, count, value)
            if dialog.run() != gtk.RESPONSE_YES:
                return
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
            from quodlibet import app
            app.window.playlist.enqueue(songs)

    def __redraw_current(self, player, song=None):
        self.model.current_iter = self.model.current_iter

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
                try:
                    tags = Pattern(header).tags
                except ValueError:
                    continue
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
        else: return "", False

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
            songs = self.get_songs()
            if rev:  # python sort is faster if it's presorted.
                songs.reverse()
            self.set_songs(songs)

    def set_sort_by_tag(self, tag, order=None):
        for h in self.get_columns():
            name = h.header_name
            if self.__get_sort_tag(name) == tag:
                if order: s = gtk.SORT_DESCENDING
                else: s = gtk.SORT_ASCENDING
                h.set_sort_order(s)
                h.set_sort_indicator(True)
            else:
                h.set_sort_indicator(False)

    def set_model(self, model):
        super(SongList, self).set_model(model)
        self.model = model
        self.set_search_column(0)

    def get_songs(self):
        try: return self.get_model().get()
        except AttributeError: return [] # model is None

    def __get_sort_tag(self, tag):
        replace_order = {
            "~#track": "",
            "~#disc": "",
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

    def add_songs(self, songs):
        """Add songs to the list in the right order and position"""

        if not songs: return

        model = self.get_model()
        if not len(model):
            self.set_songs(songs)
            return

        tag, reverse = self.get_sort_by()
        tag = self.__get_sort_tag(tag)

        if not self.is_sorted():
            self.set_sort_by_tag(tag, reverse)

        # FIXME: Replace with something fast

        old_songs = self.get_songs()
        old_songs.extend(songs)

        if not tag:
            old_songs.sort(key=lambda s: s.sort_key, reverse=reverse)
        else:
            sort_func = AudioFile.sort_by_func(tag)
            old_songs.sort(key=lambda s: s.sort_key)
            old_songs.sort(key=sort_func, reverse=reverse)

        for index, song in sorted(zip(map(old_songs.index, songs), songs)):
            model.insert(index, row=[song])

    def set_songs(self, songs, sorted=False):
        model = self.get_model()

        if not sorted:
            tag, reverse = self.get_sort_by()
            tag = self.__get_sort_tag(tag)

            #try to set a sort indicator that matches the default order
            if not self.is_sorted():
                self.set_sort_by_tag(tag, reverse)

            if not tag:
                songs.sort(key=lambda s: s.sort_key, reverse=reverse)
            else:
                sort_func = AudioFile.sort_by_func(tag)
                songs.sort(key=lambda s: s.sort_key)
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

    def get_selected_songs(self):
        selection = self.get_selection()
        if selection is None: return []
        model, rows = selection.get_selected_rows()
        return [model[row][0] for row in rows]

    def __song_updated(self, librarian, songs):
        """Only update rows that are currently displayed.
        Warning: This makes the row-changed signal useless."""
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

    def __song_added(self, librarian, songs):
        window = qltk.get_top_parent(self)
        filter_ = window.browser.active_filter
        if callable(filter_):
            self.add_songs(filter(filter_, songs))

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

        self.remove_iters(iters)

    def __song_properties(self, librarian):
        model, rows = self.get_selection().get_selected_rows()
        if rows:
            songs = [model[row][0] for row in rows]
        else:
            from quodlibet import app
            if app.player.song:
                songs = [app.player.song]
            else: return
        SongProperties(librarian, songs, parent=self)

    def __information(self, librarian):
        model, rows = self.get_selection().get_selected_rows()
        if rows:
            songs = [model[row][0] for row in rows]
        else:
            from quodlibet import app
            if app.player.song:
                songs = [app.player.song]
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
            if t in ["tracknumber", "discnumber", "language"]:
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
