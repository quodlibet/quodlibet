# -*- coding: utf-8 -*-
# Copyright 2004-2009 Joe Wreschnig, Michael Urman, Iñigo Serna,
#                     Christoph Reiter, Steven Robertson
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
from quodlibet.formats._album import Collection
from quodlibet.parse import Query, Pattern, XMLFromPattern
from quodlibet.qltk.songlist import SongList
from quodlibet.qltk.songsmenu import SongsMenu
from quodlibet.qltk.tagscombobox import TagsComboBoxEntry
from quodlibet.qltk.views import AllTreeView
from quodlibet.util import tag, pattern
from quodlibet.util.library import background_filter

class Preferences(qltk.UniqueWindow):
    def __init__(self, parent=None):
        if self.is_not_unique(): return
        super(Preferences, self).__init__()
        self.set_transient_for(qltk.get_top_parent(parent))

        self.set_border_width(12)
        self.set_resizable(False)
        self.set_title(_("Paned Browser Preferences") + " - Quod Libet")
        vb = gtk.VBox(spacing=0)
        gpa = gtk.RadioButton(None, "_" + tag("genre~~people~album"))
        gpa.headers = ["genre", "~people", "album"]
        pa = gtk.RadioButton(gpa, "_" + tag("~~people~album"))
        pa.headers = ["~people", "album"]
        headers = self.get_headers()
        custom = gtk.RadioButton(gpa, _("_Custom"))
        custom.headers = headers

        align = gtk.Alignment()
        align.set_padding(0, 0, 12, 0)
        align.add(gtk.HBox(spacing=6))

        model = gtk.ListStore(str)
        for t in headers:
            model.append(row=[t])

        view = gtk.TreeView(model)
        view.set_reorderable(True)
        view.set_headers_visible(False)
        view.set_size_request(-1, 100)

        render = gtk.CellRendererText()
        render.set_property("editable", True)
        render.connect("edited", self.__edited, model)

        col = gtk.TreeViewColumn("Tags", render, text=0)
        view.append_column(col)

        for button in [gpa, pa, custom]:
            vb.pack_start(button, expand=False)
            button.connect('toggled', self.__toggled, align, model)

        align.set_sensitive(False)
        if headers == gpa.headers: gpa.set_active(True)
        elif headers == pa.headers: pa.set_active(True)
        else: custom.set_active(True)

        vb_1 = gtk.VBox(spacing=6)
        cb = TagsComboBoxEntry(
            ["genre", "grouping", "~people", "artist", "album", "~year"])
        vb_1.pack_start(cb, expand=False)
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.add(view)
        vb_1.pack_start(sw)
        align.child.pack_start(vb_1, expand=True, fill=True)

        vb_2 = gtk.VBox(spacing=6)
        add = gtk.Button(stock=gtk.STOCK_ADD)
        add.connect('clicked', self.__add, model, cb)
        remove = gtk.Button(stock=gtk.STOCK_REMOVE)

        self.selection = view.get_selection()
        remove.connect('clicked', self.__remove, self.selection)
        self.selection.connect('changed', self.__changed, remove)
        vb_2.pack_start(add, expand=False)
        vb_2.pack_start(remove, expand=False)
        align.child.pack_start(vb_2, expand=False, fill=False)

        vb.pack_start(align)

        self.add(gtk.VBox(spacing=12))
        self.child.pack_start(vb)

        apply = gtk.Button(stock=gtk.STOCK_APPLY)
        model.connect('row-deleted', self.__row_deleted, apply)
        model.connect('row-inserted', self.__row_inserted, apply)
        apply.connect('clicked', self.__apply, model)
        box = gtk.HButtonBox()
        box.set_layout(gtk.BUTTONBOX_END)
        box.pack_start(apply)
        self.child.pack_start(box, expand=False)

        self.show_all()

    @staticmethod
    def get_headers():
        #<=2.1 saved the headers tab seperated, but had a space seperated
        #default value, so check for that.
        headers = config.get("browsers", "panes")
        if headers == "~people album":
            return headers.split()
        else:
            return headers.split("\t")

    def __add(self, button, model, cb):
        model.append(row=[cb.tag])

    def __remove(self, button, selection):
        model, iter = selection.get_selected()
        if iter: model.remove(iter)

    def __changed(self, selection, remove):
        remove.set_sensitive(bool(selection.get_selected()[1]))

    def __edited(self, render, path, text, model):
        model[path][0] = text

    def __row_deleted(self, model, path, button):
        button.set_sensitive(len(model) > 0)

    def __row_inserted(self, model, path, iter, button):
        button.set_sensitive(len(model) > 0)

    def __apply(self, button, model):
        headers = "\t".join([row[0] for row in model])
        config.set("browsers", "panes", headers)
        PanedBrowser.set_all_panes()

    def __toggled(self, button, align, model):
        if button.headers:
            model.clear()
            for h in button.headers:
                model.append(row=[h])
        align.set_sensitive(button.get_label() == _("_Custom"))

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
            super(PanedBrowser.Pane, self).__init__()
            self.set_fixed_height_mode(True)

            title, self.tags, self.__format, \
                self.__markup, disp_format = self.__parse_prefs(prefs)

            self.__next = next
            self.__model = model = gtk.ListStore(int, object)

            self.__sort_cache = {}
            self.__key_cache = {}

            column = gtk.TreeViewColumn()
            label = gtk.Label(title)
            label.set_use_markup(True)
            column.set_widget(label)
            label.show()
            column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            column.set_fixed_width(50)

            column.pack_start(self.__render)
            column.set_cell_data_func(self.__render,
                self.__text_cdf, self.__markup)
            column.pack_start(self.__render_count, expand=False)
            column.set_cell_data_func(self.__render_count,
                self.__count_cdf, disp_format)

            self.append_column(column)
            self.set_model(model)

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

        def __drag_data_get(self, view, ctx, sel, tid, etime):
            songs = self.__get_selected_songs(sort=True)
            if tid == 1:
                filenames = [song("~filename") for song in songs]
                sel.set("text/x-quodlibet-songs", 8, "\x00".join(filenames))
            else: sel.set_uris([song("~uri") for song in songs])

        @staticmethod
        def __parse_prefs(row_pattern):
            """
            Row pattern format: 'categorize_pattern:display_pattern'

            * display_pattern is optional (fallback: ~#tracks)
            * patterns, tied and normal tags.
            * display patterns can have function prefixes for numerical tags.
            * ':' has to be escaped ('\:')

            TODO: sort pattern, filter query
            """

            parts = re.split(r"(?<!\\):", row_pattern)
            parts = map(lambda p: p.replace("\:", ":"), parts)

            is_numeric = lambda s: s[:2] == "~#" and "~" not in s[2:]
            is_pattern = lambda s: '<' in s
            f_round = lambda s: (isinstance(s, float) and "%.2f" % s) or s

            disp = (len(parts) >= 2 and parts[1]) or "\<i\>(<~#tracks>)\</i\>"
            cat = parts[0]

            if is_pattern(cat):
                title = pattern(cat, esc=True)
                try: pc = XMLFromPattern(cat)
                except ValueError: pc = XMLFromPattern("")
                tags = pc.real_tags(cond=False)
                format = pc.format_list
                format_markup = True
            else:
                title = tag(cat)
                tags = util.tagsplit(cat)
                format_markup = False
                if is_numeric(cat):
                    format = lambda song: [unicode(f_round(song(cat)))]
                else:
                    format = lambda song: song.list_separate(cat)

            if is_pattern(disp):
                try: pd = XMLFromPattern(disp)
                except ValueError: pd = XMLFromPattern("")
                format_display = pd.format
            else:
                if is_numeric(disp):
                    format_display = lambda coll: unicode(f_round(coll(disp)))
                else:
                    format_display = lambda coll: util.escape(coll.comma(disp))

            return title, tags, format, format_markup, format_display

        def __get_format_keys(self, song):
            try: return self.__key_cache[song]
            except KeyError:
                # We filter out empty values, so Unknown can be ""
                self.__key_cache[song] = filter(None, self.__format(song))
                return self.__key_cache[song]

        def __human_sort_key(self, text, reg=re.compile('<.*?>')):
            try: return self.__sort_cache[text]
            except KeyError:
                # remove the markup so it doesn't affect the sort order
                if self.__markup: text = reg.sub("", text)
                self.__sort_cache[text] = util.human_sort_key(text)
                return self.__sort_cache[text]

        def __popup_menu(self, view, library):
            songs = self.__get_selected_songs(sort=True)
            menu = SongsMenu(library, songs, parent=self)
            menu.show_all()
            return view.popup_menu(menu, 0, gtk.get_current_event_time())

        def __selection_changed(self, selection):
            if not self.__next: return
            self.__next.fill(self.__get_selected_songs())

        def _remove(self, songs, remove_if_empty=True):
            self.inhibit()
            model = self.__model
            songs = set(songs)
            to_remove = []
            map(self.__key_cache.pop, songs)
            for row in model:
                type, data = row
                if type == ALL: continue
                data.songs -= songs
                data.finalize()
                model.row_changed(row.path, row.iter)
                if not data.songs:
                    to_remove.append(row.iter)
            if remove_if_empty:
                for iter in to_remove:
                    try: del(self.__sort_cache[model[iter][1].key])
                    except KeyError: pass
                    model.remove(iter)
                if len(model) == 1 and model[0][0] == ALL:
                    model.clear()
                elif to_remove and len(model) == 2:
                    model.remove(model.get_iter(0))
            self.uninhibit()

        def _matches(self, song):
            model, rows = self.get_selection().get_selected_rows()
            if not rows or model[rows[0]][0] == ALL: return True
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
                if type != SONGS: continue

                if key is None:
                    if not items: break
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
            if key: items.append((key, (val, sort_key)))

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

        def inhibit(self): self.get_selection().handler_block(self.__sig)
        def uninhibit(self): self.get_selection().handler_unblock(self.__sig)

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
            if len(model) == len(selected): selected = None
            self.inhibit()
            self.set_model(None)
            model.clear()
            self._add(songs)
            self.set_model(model)
            self.uninhibit()
            self.set_selected(selected, jump=True)
            if not songs: self.__next.fill([])

        def scroll(self, song):
            values = self.__get_format_keys(song)
            for row in self.__model:
                if row[0] != ALL and row[1].key in values:
                    self.scroll_to_cell(
                        row.path[0], use_align=True, row_align=0.5)
                    sel = self.get_selection()
                    sel.unselect_all()
                    sel.select_path(row.path[0])
                    break

        def get_selected(self):
            try: model, paths = self.get_selection().get_selected_rows()
            except AttributeError: return []
            else:
                if not paths: return []
                if model[paths[0]][0] == ALL:
                    return [model[p][1].key for p in paths[1:]] + [None]
                else:
                    return [model[p][1].key for p in paths]

        def set_selected(self, values, jump=False):
            model = self.__model
            if not len(model): return

            if not values: values = [None]

            # If the selection is the same, change nothing
            selection = self.get_selection()
            if values != self.get_selected():
                self.inhibit()
                selection.unselect_all()

                for row in model:
                    if row[0] == ALL:
                        if None in values:
                            selection.select_path(row.path)
                    else:
                        if row[1].key in values:
                            selection.select_path(row.path)

                # We didn't find something to select, so select All
                model, paths = selection.get_selected_rows()
                if not paths: selection.select_path((0,))
                self.uninhibit()

            if jump:
                model, paths = selection.get_selected_rows()
                for path in paths:
                    self.scroll_to_cell(path)
                    break

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
            if not rows: return s
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

    def __init__(self, library, player):
        super(PanedBrowser, self).__init__(library, player, limit=False)

        self._register_instance()
        self.__save = player

        self.accelerators = gtk.AccelGroup()
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

    def _text_parse(self, text):
        if Query.is_parsable(text):
            self._text = text.decode('utf-8')
            star = dict.fromkeys(SongList.star)
            star.update(self.__star)
            self._filter = Query(self._text, star.keys()).search
            self.activate()

    def activate(self):
        songs = filter(self._filter, self._library)
        bg = background_filter()
        if bg: songs = filter(bg, songs)
        self.__panes[0].fill(songs)

    def scroll(self, song):
        for pane in self.__panes:
            pane.scroll(song)

    def refresh_panes(self):
        try: hbox = self.get_children()[1]
        except IndexError: pass # first call
        else: hbox.destroy()

        hbox = gtk.HBox(spacing=6)
        hbox.set_homogeneous(True)
        hbox.set_size_request(100, 100)
        # fill in the pane list. the last pane reports back to us.
        self.__panes = [self]
        panes = Preferences.get_headers()
        panes.reverse()
        for pane in panes:
            self.__panes.insert(
                0, self.Pane(pane, self.__panes[0], self._library))
        self.__panes.pop() # remove self

        for pane in self.__panes:
            if self.__save: pane.connect('row-activated', self.__start)
            sw = gtk.ScrolledWindow()
            sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
            sw.set_shadow_type(gtk.SHADOW_IN)
            sw.add(pane)
            hbox.pack_start(sw)

        self.pack_start(hbox)
        self.show_all()

        self.__star = {}
        for p in self.__panes: self.__star.update(dict.fromkeys(p.tags))

    def fill_panes(self):
        self.__panes[-1].inhibit()
        self.activate()
        self.__panes[-1].uninhibit()

    def __start(self, view, indices, col):
        self.__save.reset()

    def __get_filter_pane(self, key):
        """Get the best pane for filtering etc."""
        canditates = []
        for pane in self.__panes:
            if (key in pane.tags or
                (key in PEOPLE and "~people" in pane.tags)):
                canditates.append((len(pane.tags), pane))
        canditates.sort()
        return (canditates and canditates[0][1]) or None

    def can_filter(self, key):
        if key is None: return True
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
            if all: values.remove(None)
            all = str(int(bool(all)))
            values.insert(0, all)

            # the config lib strips all whitespace, so add a bogus . at the end
            selected.append("\t".join(values)+ "\t.")
        config.set("browsers", "pane_selection", "\n".join(selected))

    def restore(self):
        super(PanedBrowser, self).restore()
        selected = config.get("browsers", "pane_selection")
        if not selected: return
        pane_values = [sel.split("\t") for sel in selected.split("\n")]
        for pane in pane_values:
            try:
                if int(pane[0]):
                    pane[0] = None
                else: del pane[0]
            except (ValueError, IndexError): pass
        PanedBrowser.Pane.set_restore(pane_values)

    def finalize(self, restored):
        super(PanedBrowser, self).finalize(restored)
        if not restored:
            self.fill_panes()

    def fill(self, songs):
        if self.__save: self.save()
        gobject.idle_add(self.emit, 'songs-selected', list(songs), None)

browsers = [PanedBrowser]
