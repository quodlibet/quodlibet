# -*- coding: utf-8 -*-
# Copyright 2004-2011 Joe Wreschnig, Michael Urman, Iñigo Serna,
#                     Christoph Reiter, Steven Robertson, Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import re
import operator

import gobject
import gtk
import pango

from quodlibet import config
from quodlibet import qltk
from quodlibet import util

from quodlibet.browsers.search import SearchBar
from quodlibet.formats import PEOPLE
from quodlibet.util.collection import Collection
from quodlibet.parse import Query, XMLFromPattern
from quodlibet.qltk.songlist import SongList
from quodlibet.qltk.songsmenu import SongsMenu
from quodlibet.qltk.tagscombobox import TagsComboBoxEntry
from quodlibet.qltk.views import AllTreeView, BaseView, TreeViewColumn
from quodlibet.qltk.x import ScrolledWindow
from quodlibet.util import tag, pattern
from quodlibet.util.library import background_filter


def get_headers():
    #<=2.1 saved the headers tab seperated, but had a space seperated
    #default value, so check for that.
    headers = config.get("browsers", "panes")
    if headers == "~people album":
        return headers.split()
    else:
        return headers.split("\t")


def save_headers(headers):
    headers = "\t".join(headers)
    config.set("browsers", "panes", headers)


class PatternEditor(gtk.VBox):

    PRESETS = [
            ["genre", "~people", "album"],
            ["~people", "album"],
        ]

    COMPLETION = ["genre", "grouping", "~people", "artist", "album", "~year"]

    def __init__(self):
        super(PatternEditor, self).__init__(spacing=6)

        self.__headers = headers = {}
        buttons = []

        group = None
        for tags in self.PRESETS:
            tied = "~" + "~".join(tags)
            group = gtk.RadioButton(group, "_" + tag(tied))
            headers[group] = tags
            buttons.append(group)

        group = gtk.RadioButton(group, _("_Custom"))
        self.__custom = group
        headers[group] = []
        buttons.append(group)

        button_box = gtk.HBox(spacing=6)
        self.__model = model = gtk.ListStore(str)

        radio_box = gtk.VBox(spacing=6)
        for button in buttons:
            radio_box.pack_start(button, expand=False)
            button.connect('toggled', self.__toggled, button_box, model)

        self.pack_start(radio_box, expand=False)

        cb = TagsComboBoxEntry(self.COMPLETION)

        view = BaseView(model)
        view.set_reorderable(True)
        view.set_headers_visible(False)

        ctrl_box = gtk.VBox(spacing=6)

        add = gtk.Button(stock=gtk.STOCK_ADD)
        ctrl_box.pack_start(add, expand=False)
        add.connect('clicked', self.__add, model, cb)

        remove = gtk.Button(stock=gtk.STOCK_REMOVE)
        ctrl_box.pack_start(remove, expand=False)
        remove.connect('clicked', self.__remove, view)

        selection = view.get_selection()
        selection.connect('changed', self.__selection_changed, remove)
        selection.emit('changed')

        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.add(view)

        edit_box = gtk.VBox(spacing=6)
        edit_box.pack_start(cb, expand=False)
        edit_box.pack_start(sw)

        button_box.pack_start(edit_box)
        button_box.pack_start(ctrl_box, expand=False)
        self.pack_start(button_box)

        render = gtk.CellRendererText()
        render.set_property("editable", True)

        def edited_cb(render, path, text, model):
            model[path][0] = text
        render.connect("edited", edited_cb, model)

        column = gtk.TreeViewColumn(None, render, text=0)
        view.append_column(column)

    def __get_headers(self):
        for button in self.__headers.iterkeys():
            if button.get_active():
                if button == self.__custom:
                    model_headers = [row[0] for row in self.__model]
                    self.__headers[self.__custom] = model_headers
                return self.__headers[button]

    def __set_headers(self, new_headers):
        for button, headers in self.__headers.iteritems():
            if headers == new_headers:
                button.set_active(True)
                button.emit("toggled")
                break
        else:
            self.__headers[self.__custom] = new_headers
            self.__custom.set_active(True)

    headers = property(__get_headers, __set_headers)

    def __selection_changed(self, selection, remove):
        remove.set_sensitive(bool(selection.get_selected()[1]))

    def __add(self, button, model, cb):
        if cb.tag:
            model.append(row=[cb.tag])

    def __remove(self, button, view):
        view.remove_selection()

    def __toggled(self, button, edit_widget, model):
        tags = self.__headers[button]

        if tags:
            model.clear()
            for h in tags:
                model.append(row=[h])

        edit_widget.set_sensitive(
            button.get_active() and button is self.__custom)


class Preferences(qltk.UniqueWindow):
    def __init__(self, parent=None):
        if self.is_not_unique():
            return
        super(Preferences, self).__init__()

        self.set_transient_for(qltk.get_top_parent(parent))
        self.set_default_size(350, 270)
        self.set_border_width(12)

        self.set_title(_("Paned Browser Preferences") + " - Quod Libet")

        vbox = gtk.VBox(spacing=12)

        editor = PatternEditor()
        editor.headers = get_headers()

        apply = gtk.Button(stock=gtk.STOCK_APPLY)
        apply.connect_object("clicked", self.__apply, editor, False)

        cancel = gtk.Button(stock=gtk.STOCK_CANCEL)
        cancel.connect("clicked", lambda x: self.destroy())

        ok = gtk.Button(stock=gtk.STOCK_OK)
        ok.connect_object("clicked", self.__apply, editor, True)

        box = gtk.HButtonBox()
        box.set_spacing(6)
        box.set_layout(gtk.BUTTONBOX_END)
        box.pack_start(apply)
        box.pack_start(cancel)
        box.pack_start(ok)

        vbox.pack_start(editor)
        vbox.pack_start(box, expand=False)

        self.add(vbox)

        ok.grab_focus()
        self.show_all()

    def __apply(self, editor, close):
        if editor.headers != get_headers():
            save_headers(editor.headers)
            PanedBrowser.set_all_panes()

        if close:
            self.destroy()


ALL, SONGS, UNKNOWN = range(3)
UNKNOWN_MARKUP = "<b>%s</b>" % _("Unknown")
ALL_MARKUP = "<b>%s</b>" % _("All")


class SongSelection(Collection):
    def __init__(self, key):
        super(SongSelection, self).__init__()
        self.songs = set()
        self.key = key

    def all_have(self, key, value):
        """Check if all songs have the give tag and it contains the value.
        Used for filtering.."""
        if key[:2] == "~#" and "~" not in key[2:]:
            for song in self.songs:
                if song(key) != value:
                    return False
        else:
            for song in self.songs:
                if value not in song.list(key):
                    return False
        return True


class PanePattern(object):
    """Row pattern format: 'categorize_pattern:display_pattern'

    * display_pattern is optional (fallback: ~#tracks)
    * patterns, tied and normal tags.
    * display patterns can have function prefixes for numerical tags.
    * ':' has to be escaped ('\:')

    TODO: sort pattern, filter query

    """

    def __init__(self, row_pattern):
        parts = re.split(r"(?<!\\):", row_pattern)
        parts = map(lambda p: p.replace("\:", ":"), parts)

        is_numeric = lambda s: s[:2] == "~#" and "~" not in s[2:]
        is_pattern = lambda s: '<' in s
        f_round = lambda s: (isinstance(s, float) and "%.2f" % s) or s

        disp = (len(parts) >= 2 and parts[1]) or "\<i\>(<~#tracks>)\</i\>"
        cat = parts[0]

        if is_pattern(cat):
            title = pattern(cat, esc=True)
            try:
                pc = XMLFromPattern(cat)
            except ValueError:
                pc = XMLFromPattern("")
            tags = pc.tags
            format = pc.format_list
            has_markup = True
        else:
            title = tag(cat)
            tags = util.tagsplit(cat)
            has_markup = False
            if is_numeric(cat):
                format = lambda song: [unicode(f_round(song(cat)))]
            else:
                format = lambda song: song.list_separate(cat)

        if is_pattern(disp):
            try:
                pd = XMLFromPattern(disp)
            except ValueError:
                pd = XMLFromPattern("")
            format_display = pd.format
        else:
            if is_numeric(disp):
                format_display = lambda coll: unicode(f_round(coll(disp)))
            else:
                format_display = lambda coll: util.escape(coll.comma(disp))

        self.title = title
        self.tags = set(tags)
        self.format = format
        self.format_display = format_display
        self.has_markup = has_markup

    def __repr__(self):
        return "<%s title=%r>" % (self.__class__.__name__, self.title)


class Pane(AllTreeView):
    __render = gtk.CellRendererText()
    __render.set_property('ellipsize', pango.ELLIPSIZE_END)

    __render_count = gtk.CellRendererText()
    __render_count.set_property('xalign', 1.0)

    __restore_values = None

    @classmethod
    def set_restore(klass, selected):
        klass.__restore_values = selected

    @staticmethod
    def __count_cdf(column, cell, model, iter, display_pattern):
        type, songs = model[iter]
        if type != ALL:
            cell.markup = display_pattern(songs)
        else:
            cell.markup = ""
        cell.set_property('markup', cell.markup)

    @staticmethod
    def __text_cdf(column, cell, model, iter, markup):
        type, songs = model[iter]
        if type == SONGS:
            if markup:
                cell.markup = songs.key
                cell.set_property('markup', cell.markup)
            else:
                cell.markup = None
                cell.set_property('text', songs.key)
        else:
            if type == ALL:
                cell.markup = ALL_MARKUP
            else:
                cell.markup = UNKNOWN_MARKUP
            cell.set_property('markup', cell.markup)

    def __init__(self, prefs, next, library):
        super(Pane, self).__init__()
        self.set_fixed_height_mode(True)

        self.pattern = PanePattern(prefs)
        self.tags = self.pattern.tags

        self.__next = next
        self.__model = model = gtk.ListStore(int, object)

        self.__sort_cache = {}
        self.__key_cache = {}

        column = TreeViewColumn(self.pattern.title)
        column.set_use_markup(True)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_fixed_width(50)

        column.pack_start(self.__render)
        column.set_cell_data_func(self.__render,
            self.__text_cdf, self.pattern.has_markup)
        column.pack_start(self.__render_count, expand=False)
        column.set_cell_data_func(self.__render_count,
            self.__count_cdf, self.pattern.format_display)

        self.append_column(column)
        self.set_model(model)

        self.set_search_equal_func(self.__search_func)

        selection = self.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        self.__sig = selection.connect('changed', self.__selection_changed)
        s = self.connect('popup-menu', self.__popup_menu, library)
        self.connect_object('destroy', self.disconnect, s)

        targets = [("text/x-quodlibet-songs", gtk.TARGET_SAME_APP, 1),
               ("text/uri-list", 0, 2)]
        self.drag_source_set(
            gtk.gdk.BUTTON1_MASK, targets, gtk.gdk.ACTION_COPY)
        self.connect("drag-data-get", self.__drag_data_get)

        self.connect("destroy", self.__destroy)

    def __destroy(self, *args):
        # needed for gc
        self.__next = None

    def __search_func(self, model, column, key, iter):
        type, data = model[iter]
        key = key.decode('utf-8').lower()
        if type == SONGS and key in data.key.lower():
            return False
        return True

    def __drag_data_get(self, view, ctx, sel, tid, etime):
        songs = self.__get_selected_songs(sort=True)
        if tid == 1:
            filenames = [song("~filename") for song in songs]
            sel.set("text/x-quodlibet-songs", 8, "\x00".join(filenames))
        else:
            sel.set_uris([song("~uri") for song in songs])

    def __get_format_keys(self, song):
        try:
            return self.__key_cache[song]
        except KeyError:
            # We filter out empty values, so Unknown can be ""
            self.__key_cache[song] = filter(None, self.pattern.format(song))
            return self.__key_cache[song]

    def __human_sort_key(self, text, reg=re.compile('<.*?>')):
        try:
            return self.__sort_cache[text]
        except KeyError:
            # remove the markup so it doesn't affect the sort order
            if self.pattern.has_markup:
                text = reg.sub("", text)
            self.__sort_cache[text] = util.human_sort_key(text)
            return self.__sort_cache[text]

    def __popup_menu(self, view, library):
        songs = self.__get_selected_songs(sort=True)
        menu = SongsMenu(library, songs, parent=self)
        menu.show_all()
        return view.popup_menu(menu, 0, gtk.get_current_event_time())

    def __selection_changed(self, selection):
        if not self.__next:
            return
        self.__next.fill(self.__get_selected_songs())

    def _remove(self, songs, remove_if_empty=True):
        self.inhibit()
        model = self.__model
        songs = set(songs)
        to_remove = []
        for song in songs:
            if song in self.__key_cache:
                del self.__key_cache[song]
        for row in model:
            type, data = row
            if type == ALL:
                continue
            data.songs -= songs
            data.finalize()
            model.row_changed(row.path, row.iter)
            if not data.songs:
                to_remove.append(row.iter)
        if remove_if_empty:
            for iter in to_remove:
                try:
                    del(self.__sort_cache[model[iter][1].key])
                except KeyError:
                    pass
                model.remove(iter)
            if len(model) == 1 and model[0][0] == ALL:
                model.clear()
            elif to_remove and len(model) == 2:
                model.remove(model.get_iter(0))
        self.uninhibit()

    def _matches(self, song):
        model, rows = self.get_selection().get_selected_rows()
        if not rows or model[rows[0]][0] == ALL:
            return True
        keys = self.__get_format_keys(song)
        if not keys and model[rows[-1]][0] == UNKNOWN:
            return True
        for row in rows:
            if model[row][1].key in keys:
                return True
        return False

    def _add(self, songs):
        collection = {}
        unknown = SongSelection("")
        human_sort = self.__human_sort_key
        for song in songs:
            keys = self.__get_format_keys(song)
            if not keys:
                unknown.songs.add(song)
            for key in keys:
                try:
                    collection[key][0].songs.add(song)
                except KeyError:
                    collection[key] = (SongSelection(key), human_sort(key))
                    collection[key][0].songs.add(song)

        items = sorted(collection.iteritems(),
            key=lambda s: s[1][1], reverse=True)

        # faster...
        model = self.__model
        if not len(model):
            insert = model.insert
            if unknown.songs:
                insert(0, [UNKNOWN, unknown])
            for key, (val, sort_key) in items:
                insert(0, [SONGS, val])
            if len(model) > 1:
                insert(0, [ALL, None])
            return

        # insert all new songs
        key = None
        val = None
        sort_key = None
        for row in self.__model:
            type, data = row
            if type != SONGS:
                continue

            if key is None:
                if not items:
                    break
                key, (val, sort_key) = items.pop(-1)

            if key == data.key:
                data.songs |= val.songs
                data.finalize()
                model.row_changed(row.path, row.iter)
                key = None
            elif sort_key < human_sort(data.key):
                model.insert_before(row.iter, row=[SONGS, val])
                key = None

        # the last one failed, add it again
        if key:
            items.append((key, (val, sort_key)))

        # insert the left over songs
        if items:
            if model[-1][0] == UNKNOWN:
                for key, (val, srt) in reversed(items):
                    model.insert(len(model) - 1, row=[SONGS, val])
            else:
                for key, (val, srt) in items:
                    model.append(row=[SONGS, val])

        # check if All needs to be inserted
        if len(model) > 1 and model[0][0] != ALL:
            model.insert(0, [ALL, None])

        # check if Unknown needs to be inserted or updated
        if unknown.songs:
            last_row = model[-1]
            type, data = last_row
            if type == UNKNOWN:
                data.songs |= unknown.songs
                data.finalize()
                model.row_changed(last_row.path, last_row.iter)
            else:
                model.append(row=[UNKNOWN, unknown])

    def inhibit(self):
        self.get_selection().handler_block(self.__sig)

    def uninhibit(self):
        self.get_selection().handler_unblock(self.__sig)

    def list(self, key):
        #We get all tag values and check if all songs have it.
        model = self.__model
        # If the key is the only tag, return everything
        if len(self.tags) == 1 and key in self.tags:
            return [r[1].key for r in model if r[0] != ALL]
        # For patterns/tied tags we have to make sure that
        # filtering for that key will return only songs that all have
        # the specified value
        all = set()
        sels = (row[1] for row in model if row[0] == SONGS)
        for sel in sels:
            values = sel.list(key)
            for value in values:
                if value not in all and sel.all_have(key, value):
                    all.add(value)
        # Also add unknown
        if len(model) > 0 and model[-1][0] == UNKNOWN:
            all.add("")
        return list(all)

    def fill(self, songs):
        # restore the selection
        restore = self.__restore_values
        selected = (restore and restore.pop(0)) or self.get_selected()
        model = self.__model
        # if previously all entries were selected: select All
        if len(model) == len(selected):
            selected = None
        self.inhibit()
        self.set_model(None)
        model.clear()
        self._add(songs)
        self.set_model(model)
        self.uninhibit()
        self.set_selected(selected, jump=True)
        if not songs:
            self.__next.fill([])

    def scroll(self, song):
        values = self.__get_format_keys(song)
        select_func = lambda r: r[0] != ALL and r[1].key in values
        self.select_by_func(select_func, one=True)

    def get_selected(self):
        try:
            model, paths = self.get_selection().get_selected_rows()
        except AttributeError:
            return []
        else:
            if not paths:
                return []
            if model[paths[0]][0] == ALL:
                return [model[p][1].key for p in paths[1:]] + [None]
            else:
                return [model[p][1].key for p in paths]

    def set_selected(self, values, jump=False):
        if not len(self.__model):
            return

        values = values or [None]

        def select_func(row):
            return (row[0] == ALL and None in values) or \
                   (row[0] == SONGS and row[1].key in values)

        # If the selection is the same, change nothing
        if values != self.get_selected():
            self.inhibit()
            if not self.select_by_func(select_func, scroll=jump):
                self.set_cursor((0,))
            self.uninhibit()

        self.get_selection().emit('changed')

    def set_selected_by_tag(self, tag, values, jump=False):
        """Select the entries which songs all have one of the values."""
        # Like with self.list we can select all matching keys if the tag
        # is our only tag
        if len(self.tags) == 1 and tag in self.tags:
            self.set_selected(values, jump)
            return
        pattern_values = []
        for type, data in self.__model:
            if type == SONGS:
                for value in values:
                    if data.all_have(tag, value):
                        pattern_values.append(data.key)
                        break
        # select unknown
        if "" in values:
            pattern_values.append("")
        self.set_selected(pattern_values, jump)

    def __get_selected_songs(self, sort=False):
        model, rows = self.get_selection().get_selected_rows()
        s = set()
        if not rows:
            return s
        if model[rows[0]][0] == ALL:
            for row in model:
                if row[0] != ALL:
                    s |= row[1].songs
        else:
            for row in rows:
                s |= model[row][1].songs
        if sort:
            return sorted(s, key=operator.attrgetter("sort_key"))
        return s


class PanedBrowser(SearchBar, util.InstanceTracker):
    expand = qltk.RVPaned

    name = _("Paned Browser")
    accelerated_name = _("_Paned Browser")
    priority = 3

    def set_all_panes(klass):
        for browser in klass.instances():
            browser.refresh_panes()
            browser.fill_panes()
    set_all_panes = classmethod(set_all_panes)

    def __init__(self, library, main):
        super(PanedBrowser, self).__init__(library, main, limit=False)

        self._register_instance()
        self.__main = main

        keyval, mod = gtk.accelerator_parse("<control>Home")
        s = self.accelerators.connect_group(keyval, mod, 0, self.__all)
        self.connect_object('destroy',
            self.accelerators.disconnect_key, keyval, mod)
        select = gtk.Button(_("Select _All"))
        self._search_bar.pack_start(select, expand=False)

        prefs = gtk.Button()
        prefs.add(gtk.image_new_from_stock(
            gtk.STOCK_PREFERENCES, gtk.ICON_SIZE_MENU))
        s = prefs.connect('clicked', Preferences)
        self.connect_object('destroy', prefs.disconnect, s)
        s = select.connect('clicked', self.__all)
        self.connect_object('destroy', select.disconnect, s)
        self._search_bar.pack_start(prefs, expand=False)

        for s in [library.connect('changed', self.__changed),
                  library.connect('added', self.__added),
                  library.connect('removed', self.__removed)
                  ]:
            self.connect_object('destroy', library.disconnect, s)

        self.refresh_panes()
        self.show_all()

    def __all(self, *args):
        self.__panes[-1].inhibit()
        for pane in self.__panes:
            pane.set_selected(None, True)
        self.__panes[-1].uninhibit()
        self.__panes[-1].get_selection().emit('changed')

    def __added(self, library, songs):
        songs = filter(self._filter, songs)
        for pane in self.__panes:
            pane._add(songs)
            songs = filter(pane._matches, songs)

    def __removed(self, library, songs, remove_if_empty=True):
        songs = filter(self._filter, songs)
        for pane in self.__panes:
            pane._remove(songs, remove_if_empty)

    def __changed(self, library, songs):
        self.__removed(library, songs, False)
        self.__added(library, songs)
        self.__removed(library, [])

    def active_filter(self, song):
        # check with the search filter
        if not self._filter(song):
            return False

        # check if the selection is right in every pane
        for pane in self.__panes:
            if not pane._matches(song):
                return False

        return True

    def activate(self):
        if self._text is not None and Query.is_parsable(self._text):
            star = dict.fromkeys(SongList.star)
            star.update(self.__star)
            self._filter = Query(self._text, star.keys()).search
            songs = filter(self._filter, self._library)
            bg = background_filter()
            if bg:
                songs = filter(bg, songs)
            self.__panes[0].fill(songs)

    def scroll(self, song):
        for pane in self.__panes:
            pane.scroll(song)

    def refresh_panes(self):
        try:
            hbox = self.get_children()[1]
        except IndexError:
            pass  # first call
        else:
            hbox.destroy()

        hbox = gtk.HBox(spacing=6)
        hbox.set_homogeneous(True)
        hbox.set_size_request(100, 100)
        # fill in the pane list. the last pane reports back to us.
        self.__panes = [self]
        panes = get_headers()
        panes.reverse()
        for pane in panes:
            self.__panes.insert(
                0, Pane(pane, self.__panes[0], self._library))
        self.__panes.pop()  # remove self

        for pane in self.__panes:
            if self.__main:
                pane.connect('row-activated',
                             lambda *x: self.emit("activated"))
            sw = ScrolledWindow()
            sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
            sw.set_shadow_type(gtk.SHADOW_IN)
            sw.add(pane)
            hbox.pack_start(sw)

        self.pack_start(hbox)
        self.show_all()

        self.__star = {}
        for p in self.__panes:
            self.__star.update(dict.fromkeys(p.tags))

    def fill_panes(self):
        self.__panes[-1].inhibit()
        self.activate()
        self.__panes[-1].uninhibit()

    def __get_filter_pane(self, key):
        """Get the best pane for filtering etc."""
        canditates = []
        for pane in self.__panes:
            if (key in pane.tags or
                (key in PEOPLE and "~people" in pane.tags)):
                canditates.append((len(pane.tags), pane))
        canditates.sort()
        return (canditates and canditates[0][1]) or None

    def can_filter_tag(self, key):
        return (self.__get_filter_pane(key) is not None)

    def filter(self, key, values):
        filter_pane = self.__get_filter_pane(key)

        for pane in self.__panes:
            if pane is filter_pane:
                filter_pane.set_selected_by_tag(key, values, True)
                return
            pane.set_selected(None, True)

    def unfilter(self):
        self.filter("", "")

    def list(self, key):
        filter_pane = self.__get_filter_pane(key)
        if filter_pane is None:
            return super(PanedBrowser, self).list(key)

        for pane in self.__panes:
            if pane is filter_pane:
                return filter_pane.list(key)
            pane.set_selected(None, True)
        return []

    def save(self):
        super(PanedBrowser, self).save()
        selected = []
        for pane in self.__panes:
            values = pane.get_selected()

            # The first value tells us if All was selected
            all = None in values
            if all:
                values.remove(None)
            all = str(int(bool(all)))
            values.insert(0, all)

            # the config lib strips all whitespace, so add a bogus . at the end
            selected.append("\t".join(values) + "\t.")
        config.set("browsers", "pane_selection", "\n".join(selected))

    def restore(self):
        super(PanedBrowser, self).restore(activate=False)
        selected = config.get("browsers", "pane_selection")
        if not selected:
            return
        pane_values = [sel.split("\t") for sel in selected.split("\n")]
        for pane in pane_values:
            try:
                if int(pane[0]):
                    pane[0] = None
                else:
                    del pane[0]
            except (ValueError, IndexError):
                pass
        Pane.set_restore(pane_values)

    def finalize(self, restored):
        super(PanedBrowser, self).finalize(restored)
        if not restored:
            self._text = ""
            self.fill_panes()

    def fill(self, songs):
        gobject.idle_add(self.emit, 'songs-selected', list(songs), None)

browsers = [PanedBrowser]
