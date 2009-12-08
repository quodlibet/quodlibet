# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gobject
import gtk
import pango

from quodlibet import config
from quodlibet import qltk
from quodlibet import util

from quodlibet.browsers._base import Browser
from quodlibet.formats import PEOPLE
from quodlibet.parse import Query, Pattern
from quodlibet.qltk.entry import ValidatingEntry
from quodlibet.qltk.songlist import SongList
from quodlibet.qltk.songsmenu import SongsMenu
from quodlibet.qltk.tagscombobox import TagsComboBoxEntry
from quodlibet.qltk.views import AllTreeView
from quodlibet.util import tag, pattern

UNKNOWN = "<b>%s</b>" % _("Unknown")

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
        custom = gtk.RadioButton(gpa, _("_Custom"))
        custom.headers = config.get("browsers", "panes").split("\t")

        align = gtk.Alignment()
        align.set_padding(0, 0, 12, 0)
        align.add(gtk.HBox(spacing=6))

        model = gtk.ListStore(str)
        for t in config.get("browsers", "panes").split("\t"):
            model.append(row=[t])

        view = gtk.TreeView(model)
        view.set_reorderable(True)
        view.set_headers_visible(False)
        view.set_size_request(-1, 100)
        render = gtk.CellRendererText()
        render.set_property("editable", True)
        col = gtk.TreeViewColumn("Tags", render, text=0)
        view.append_column(col)

        for button in [gpa, pa, custom]:
            vb.pack_start(button, expand=False)
            button.connect('toggled', self.__toggled, align, model)

        align.set_sensitive(False)
        current = config.get("browsers", "panes").split("\t")
        if current == gpa.headers: gpa.set_active(True)
        elif current == pa.headers: pa.set_active(True)
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

    def __add(self, button, model, cb):
        model.append(row=[cb.tag])

    def __remove(self, button, selection):
        model, iter = selection.get_selected()
        if iter: model.remove(iter)

    def __changed(self, selection, remove):
        remove.set_sensitive(bool(selection.get_selected()[1]))

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

class PanedBrowser(gtk.VBox, Browser, util.InstanceTracker):
    __gsignals__ = Browser.__gsignals__
    expand = qltk.RVPaned

    name = _("Paned Browser")
    accelerated_name = _("_Paned Browser")
    priority = 3

    def set_all_panes(klass):
        for browser in klass.instances(): browser.refresh_panes()
    set_all_panes = classmethod(set_all_panes)

    class Pane(AllTreeView):
        __render = gtk.CellRendererText()
        __render.set_property('ellipsize', pango.ELLIPSIZE_END)

        __render_count = gtk.CellRendererText()
        __render_count.set_property('xalign', 1.0)

        def __count_cdf(column, cell, model, iter):
            try: cell.set_property('text', "(%d)" % (len(model[iter][1])))
            except TypeError: cell.set_property('text', '')
        __count_cdf = staticmethod(__count_cdf)

        def __init__(self, mytag, next, library):
            super(PanedBrowser.Pane, self).__init__()
            self.set_fixed_height_mode(True)

            if '<' in mytag:
                p = Pattern(mytag)
                self.__format = lambda song: [p.format(song)]
                title = pattern(mytag)
            else:
                self.__format = lambda song: song.list(mytag)
                title = tag(mytag)

            self.tags = util.tagsplit(mytag)
            self.__next = next
            model = gtk.ListStore(str, object)

            column = gtk.TreeViewColumn(title, self.__render, markup=0)
            column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            column.set_fixed_width(50)

            column.pack_start(self.__render_count, expand=False)
            column.set_cell_data_func(self.__render_count, self.__count_cdf)

            self.append_column(column)
            self.set_model(model)

            selection = self.get_selection()
            selection.set_mode(gtk.SELECTION_MULTIPLE)
            self.__sig = selection.connect('changed', self.__changed)
            self.connect_object('destroy', self.__destroy, model)
            self.connect('popup-menu', self.__popup_menu, library)

        def __popup_menu(self, view, library):
            menu = SongsMenu(library, sorted(self.__get_songs()), parent=self)
            menu.show_all()
            return view.popup_menu(menu, 0, gtk.get_current_event_time())

        def __destroy(self, model):
            self.set_model(None)
            model.clear()

        def __changed(self, selection, jump=False):
            model, rows = selection.get_selected_rows()
            if jump and rows:
                self.scroll_to_cell(rows[0][0], use_align=True, row_align=0.5)
            songs = self.__get_songs()
            if not songs: return
            self.__next.fill(songs)

        def _remove(self, songs, remove_if_empty=True):
            self.inhibit()
            model = self.get_model()
            to_remove = []
            for row in model:
                data = row[1]
                if data is None: continue
                for song in songs:
                    if song in data: data.remove(song)
                if not model[row.iter][1]: to_remove.append(row.iter)
            if remove_if_empty: map(model.remove, to_remove)
            self.uninhibit()

        def _matches(self, song):
            try: model, rows = self.get_selection().get_selected_rows()
            except (AttributeError, TypeError): return False
            else:
                if not rows or model[rows[0]][1] is None: return True
                else:
                    for row in rows:
                        if model[row][0][:1] == "<":
                            if not bool(self.__format(song)):
                                return True
                        else:
                            value = util.unescape(model[row][0])
                            if value in self.__format(song):
                                return True
                    else: return False

        def _add(self, songs):
            self.inhibit()
            model = self.get_model()
            values = {}
            new = {}
            for row in model:
                value = row[0]
                data = row[1]
                if value[:1] != "<":
                    value = util.unescape(value).decode('utf-8')
                    values[value] = data
                elif data is not None:
                    values[""] = data

            for song in songs:
                for val in (self.__format(song) or [""]):
                    if val in values: values[val].add(song)
                    else:
                        if val not in new: new[val] = set()
                        new[val].add(song)

            if new:
                keys = sorted(new.keys())
                if keys[0] == "":
                    unknown = new[""]
                    keys.pop(0)
                else: unknown = set()
                for row in model:
                    if row[0][0] == "<": continue
                    elif not keys: break

                    if util.unescape(row[0]) > keys[0]:
                        key = keys.pop(0)
                        model.insert_before(
                            row.iter, row=[util.escape(key), new[key]])
                else:
                    for key in keys:
                        model.append(row=[util.escape(key), new[key]])
                if unknown:
                    model.append(row=[UNKNOWN, new[""]])

                if (len(values) + len(new)) > 1 and model[(0,)][1] is not None:
                    model.insert(0, row=["<b>%s</b>" % _("All"), None])
            self.uninhibit()

        def inhibit(self): self.get_selection().handler_block(self.__sig)
        def uninhibit(self): self.get_selection().handler_unblock(self.__sig)

        def fill(self, songs):
            selected = self.get_selected()
            model = self.get_model()
            self.inhibit()
            model.clear()
            self._add(songs)
            self.uninhibit()
            if selected: self.set_selected(selected, jump=True)
            else: self.set_selected(None, jump=True)

        def scroll(self, song):
            values = map(util.escape, self.__format(song))
            for row in self.get_model():
                if row[0] in values:
                    self.scroll_to_cell(
                        row.path[0], use_align=True, row_align=0.5)
                    sel = self.get_selection()
                    sel.unselect_all()
                    sel.select_path(row.path[0])
                    break

        def get_selected(self):
            try: model, rows = self.get_selection().get_selected_rows()
            except AttributeError: return []
            else: return [model[row][0] for row in rows]

        def set_selected(self, values, jump=False):
            model = self.get_model()
            selection = self.get_selection()
            if values == self.get_selected(): return
            elif values is None and selection.path_is_selected((0,)): return

            self.inhibit()
            selection.unselect_all()
            first = 0
            if values is None: selection.select_path((0,))
            else:
                for row in model:
                    if row[0] in values:
                        selection.select_path(row.path)
                        first = first or row.path[0]
            if first == 0: selection.select_path((0,))
            if jump and len(model): self.scroll_to_cell(first)
            self.uninhibit()
            self.get_selection().emit('changed')

        def __get_songs(self):
            model, rows = self.get_selection().get_selected_rows()
            s = set()
            if rows and rows[0] == (0,):
                for row in model:
                    if row[1]:
                        s.update(row[1])
            else:
                for row in rows:
                    s.update(model[row][1])
            return s

    @classmethod
    def init(klass, library):
        klass.__library = library

    def __init__(self, library, player):
        super(PanedBrowser, self).__init__(spacing=6)
        eager_search = config.get("settings", "eager_search")

        self._register_instance()
        self.__save = player
        hb = gtk.HBox(spacing=6)

        hb2 = gtk.HBox(spacing=0)
        label = gtk.Label(_("_Search:"))
        label.connect('mnemonic-activate', self.__mnemonic_activate)
        #somehow, entry gets lost during "changed" otherwise...
        self.pygtkbug = search = ValidatingEntry(Query.is_valid_color)
        label.set_mnemonic_widget(search)
        label.set_use_underline(True)
        hb2.pack_start(search)
        search.pack_clear_button(hb2)
        hb.pack_start(label, expand=False)
        hb.pack_start(hb2)

        self.accelerators = gtk.AccelGroup()
        keyval, mod = gtk.accelerator_parse("<control>Home")
        self.accelerators.connect_group(keyval, mod, 0, self.__all)
        select = gtk.Button(_("Select _All"))
        hb.pack_start(select, expand=False)

        prefs = gtk.Button()
        prefs.add(
            gtk.image_new_from_stock(gtk.STOCK_PREFERENCES, gtk.ICON_SIZE_MENU))
        prefs.connect('clicked', Preferences)
        select.connect('clicked', self.__all)
        hb.pack_start(prefs, expand=False)
        self.pack_start(hb, expand=False)
        self.__refill_id = None
        self.__filter = None
        if eager_search:
            search.connect('changed', self.__filter_changed)
        else:
            search.connect('activate', self.__filter_changed)
        for s in [library.connect('changed', self.__changed),
                  library.connect('added', self.__added),
                  library.connect('removed', self.__removed)
                  ]:
            self.connect_object('destroy', library.disconnect, s)
        self.connect_object('destroy', type(self).__destroy, self)
        self.refresh_panes(restore=False)
        self.show_all()

    def __destroy(self):
        self.__save = None

    def __all(self, *args):
        self.__panes[-1].inhibit()
        for pane in self.__panes:
            pane.set_selected(None, True)
        self.__panes[-1].uninhibit()
        self.activate()

    def __mnemonic_activate(self, label, group_cycling):
        # If our mnemonic widget already has the focus, switch to
        # the song list instead. (#254)
        widget = label.get_mnemonic_widget()
        if widget.is_focus():
            qltk.get_top_parent(widget).songlist.grab_focus()
            return True

    def __filter_changed(self, entry):
        if self.__refill_id is not None:
            gobject.source_remove(self.__refill_id)
            self.__refill_id = None
        text = entry.get_text().decode('utf-8')
        if Query.is_parsable(text):
            star = dict.fromkeys(SongList.star)
            star.update(self.__star)
            if text: self.__filter = Query(text, star.keys()).search
            else: self.__filter = None
            self.__refill_id = gobject.timeout_add(500, self.activate)

    def __added(self, library, songs):
        songs = filter(self.__filter, songs)
        for pane in self.__panes:
            pane._add(songs)
            songs = filter(pane._matches, songs)

    def __removed(self, library, songs, remove_if_empty=True):
        songs = filter(self.__filter, songs)
        for pane in self.__panes:
            pane._remove(songs, remove_if_empty)

    def __changed(self, library, songs):
        self.__removed(library, songs, False)
        self.__added(library, songs)
        self.__removed(library, [])

    def activate(self):
        songs = filter(self.__filter, self.__library)
        self.__panes[0].fill(songs)

    def scroll(self, song):
        for pane in self.__panes:
            pane.scroll(song)

    def refresh_panes(self, restore=True):
        try: hbox = self.get_children()[1]
        except IndexError: pass # first call
        else: hbox.destroy()

        hbox = gtk.HBox(spacing=6)
        hbox.set_homogeneous(True)
        hbox.set_size_request(100, 100)
        # fill in the pane list. the last pane reports back to us.
        self.__panes = [self]
        panes = config.get("browsers", "panes").split("\t"); panes.reverse()
        for pane in panes:
            self.__panes.insert(
                0, self.Pane(pane, self.__panes[0], self.__library))
        self.__panes.pop() # remove self

        for pane in self.__panes:
            if self.__save: pane.connect('row-activated', self.__start)
            sw = gtk.ScrolledWindow()
            sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
            sw.set_shadow_type(gtk.SHADOW_IN)
            sw.add(pane)
            hbox.pack_start(sw)

        self.pack_start(hbox)
        self.__panes[-1].inhibit()
        self.activate()
        self.__panes[-1].uninhibit()
        if restore: self.restore()
        self.show_all()

        self.__star = {}
        for p in self.__panes: self.__star.update(dict.fromkeys(p.tags))

    def __start(self, view, indices, col):
        self.__save.reset()

    def can_filter(self, key):
        for pane in self.__panes:
            if (key in pane.tags or
                (key in PEOPLE and "~people" in pane.tags)):
                return True
        else: return False

    def filter(self, key, values):
        self.__panes[-1].inhibit()
        for pane in self.__panes:
            if (key in pane.tags or
                (key in PEOPLE and "~people" in pane.tags)):
                pane.set_selected(map(util.escape, values), True)
            else: pane.set_selected(None, True)
        self.__panes[-1].uninhibit()
        self.__panes[-1].get_selection().emit('changed')

    def unfilter(self):
        self.filter("", "")

    def list(self, key):
        for pane in self.__panes:
            if (key in pane.tags or
                (key in PEOPLE and "~people" in pane.tags)):
                return [util.unescape(row[0]) for row in pane.get_model()
                        if row[0] and not row[0].startswith("<")]
        else: return []

    def save(self):
        selected = []
        for pane in self.__panes:
            selected.append("\t".join(pane.get_selected()))
        config.set("browsers", "pane_selection", "\n".join(selected))

    def restore(self):
        selected = config.get("browsers", "pane_selection").split("\n")
        if len(selected) == len(self.__panes):
            self.__panes[-1].inhibit()
            for values, pane in zip(selected, self.__panes[:-1]):
                pane.set_selected(values.split("\t"), True)
            self.__panes[-1].uninhibit()
            self.__panes[-1].set_selected(selected[-1].split("\t"), True)

    def fill(self, songs):
        if self.__save: self.save()
        self.emit('songs-selected', list(songs), None)

browsers = [PanedBrowser]
