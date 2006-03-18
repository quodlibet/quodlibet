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
import stock
import config
import qltk
import util

from util import tag
from parse import Query
from library import library
from browsers._base import Browser
from qltk.songlist import SongList
from qltk.views import AllTreeView
from qltk.entry import ValidatingEntry
from qltk.songsmenu import SongsMenu
from qltk.tagscombobox import TagsComboBoxEntry

from formats._audio import PEOPLE
if sys.version_info < (2, 4): from sets import Set as set

UNKNOWN = "<b>%s</b>" % _("Unknown")

class Preferences(qltk.Window):
    def __init__(self, *args, **kwargs):
        super(Preferences, self).__init__(*args, **kwargs)
        self.set_border_width(12)
        self.set_resizable(False)
        self.set_title(_("Paned Browser Preferences") + " - Quod Libet")
        vb = gtk.VBox(spacing=0)
        gpa = gtk.RadioButton(None, "_" + tag("genre~~people~album"))
        gpa.headers = ["genre", "~people", "album"]
        pa = gtk.RadioButton(gpa, "_" + tag("~~people~album"))
        pa.headers = ["~people", "album"]
        custom = gtk.RadioButton(gpa, _("_Custom"))
        custom.headers = []

        align = gtk.Alignment()
        align.set_padding(0, 0, 12, 0)
        align.add(gtk.HBox(spacing=6))

        model = gtk.ListStore(str)
        for t in config.get("browsers", "panes").split():
            model.append(row=[t])

        view = gtk.TreeView(model)
        view.set_reorderable(True)
        view.set_headers_visible(False)
        view.set_size_request(-1, 100)
        col = gtk.TreeViewColumn("Tags", gtk.CellRendererText(), text=0)
        view.append_column(col)

        for button in [gpa, pa, custom]:
            vb.pack_start(button, expand=False)
            button.connect('toggled', self.__toggled, align, model)

        align.set_sensitive(False)
        current = config.get("browsers", "panes").split()
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
        remove.connect('clicked', self.__remove, view.get_selection())
        view.get_selection().connect('changed', self.__changed, remove)
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

        self.connect_object('delete-event', Preferences.__delete_event, self)
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

    def __delete_event(self, event):
        self.hide()
        return True

    def __toggled(self, button, align, model):
        if button.headers:
            model.clear()
            for h in button.headers:
                model.append(row=[h])
        align.set_sensitive(not bool(button.headers))

class PanedBrowser(gtk.VBox, Browser, util.InstanceTracker):
    __gsignals__ = Browser.__gsignals__
    expand = qltk.RVPaned

    __prefs_window = None

    def set_all_panes(klass):
        for browser in klass.instances(): browser.refresh_panes()
    set_all_panes = classmethod(set_all_panes)

    class Pane(AllTreeView):
        __render = gtk.CellRendererText()
        __render.set_property('ellipsize', pango.ELLIPSIZE_END)

        def __init__(self, mytag, next):
            super(PanedBrowser.Pane, self).__init__()
            self.tags = util.tagsplit(mytag)
            self.__next = next
            self.__mytag = mytag
            model = gtk.ListStore(str, object)

            column = gtk.TreeViewColumn(tag(mytag), self.__render, markup=0)
            column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            column.set_fixed_width(50)
            self.append_column(column)
            self.set_model(model)

            selection = self.get_selection()
            selection.set_mode(gtk.SELECTION_MULTIPLE)
            self.__sig = selection.connect('changed', self.__changed)
            self.connect_object('destroy', self.__destroy, model)
            self.connect('popup-menu', self.__popup_menu)

        def __popup_menu(self, view):
            from widgets import main, watcher
            songs = self.__get_songs()
            songs.sort()
            menu = SongsMenu(watcher, songs)
            menu.show_all()
            menu.popup(None, None, None, 0, gtk.get_current_event_time())
            return True

        def __destroy(self, model):
            self.set_model(None)
            model.clear()

        def __changed(self, selection, jump=False):
            model, rows = selection.get_selected_rows()
            if jump and rows:
                self.scroll_to_cell(rows[0][0], use_align=True, row_align=0.5)
            self.__next.fill(self.__get_songs())

        def _remove(self, songs):
            self.inhibit()
            model = self.get_model()
            to_remove = []
            for row in model:
                data = row[1]
                if data is None: continue
                for song in songs:
                    if song in data: data.remove(song)
                if not model[row.iter][1]: to_remove.append(row.iter)
            map(model.remove, to_remove)
            self.uninhibit()

        def _add(self, songs):
            self.inhibit()
            model = self.get_model()
            values = {}
            new = {}
            for row in model:
                value = row[0]
                data = row[1]
                if value[:1] != "<":
                    value = util.unescape(value)
                    values[value] = data
                elif data is not None:
                    values[""] = data

            for song in songs:
                for val in (song.list(self.__mytag) or [""]):
                    if val in values: values[val].add(song)
                    else:
                        if val not in new: new[val] = set()
                        new[val].add(song)

            if new:
                keys = new.keys()
                keys.sort()
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
            values = map(util.escape, song.list(self.__mytag))
            for row in self.get_model():
                if row[0] in values:
                    self.scroll_to_cell(
                        row.path[0], use_align=True, row_align=0.5)
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
            if rows and rows[0] == (0,):
                songs = [(row[1] or set()) for row in model]
                return list(reduce(set.union, songs, set()))
            else:
                songs = [model[row][1] for row in rows]
                if len(songs) == 1: return list(songs[0])
                else: return list(reduce(set.union, songs, set()))

    def __init__(self, watcher, player):
        super(PanedBrowser, self).__init__(spacing=6)
        self._register_instance()
        self.__save = player
        hb = gtk.HBox(spacing=6)
        hb2 = gtk.HBox(spacing=0)
        label = gtk.Label(_("_Search:"))
        label.connect('mnemonic-activate', self.__mnemonic_activate)
        search = ValidatingEntry(Query.is_valid_color)
        label.set_mnemonic_widget(search)
        label.set_use_underline(True)
        clr = gtk.Button()
        clr.add(gtk.image_new_from_stock(gtk.STOCK_CLEAR, gtk.ICON_SIZE_MENU))
        clr.connect_object('clicked', search.set_text, "")
        hb2.pack_start(search)
        hb2.pack_start(clr, expand=False)
        hb.pack_start(label, expand=False)
        hb.pack_start(hb2)

        prefs = gtk.Button()
        prefs.add(
            gtk.image_new_from_stock(gtk.STOCK_PREFERENCES, gtk.ICON_SIZE_MENU))
        prefs.connect('clicked', self.__preferences)
        hb.pack_start(prefs, expand=False)
        self.pack_start(hb, expand=False)
        self.__refill_id = None
        self.__filter = None
        search.connect('changed', self.__filter_changed)
        for s in [watcher.connect('changed', self.__changed),
                  watcher.connect('added', self.__added),
                  watcher.connect('removed', self.__removed)
                  ]:
            self.connect_object('destroy', watcher.disconnect, s)
        self.refresh_panes(restore=False)
        self.show_all()

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

    def __added(self, watcher, songs):
        for pane in self.__panes: pane._add(songs)

    def __removed(self, watcher, songs):
        for pane in self.__panes: pane._remove(songs)

    def __changed(self, watcher, songs):
        self.__removed(watcher, songs)
        self.__added(watcher, songs)

    def activate(self):
        self.__panes[0].fill(filter(self.__filter, library.values()))

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
        panes = config.get("browsers", "panes").split(); panes.reverse()
        for pane in panes:
            self.__panes.insert(0, self.Pane(pane, self.__panes[0]))
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
        self.__save.next()

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

    def __preferences(self, activator):
        if PanedBrowser.__prefs_window is None:
            PanedBrowser.__prefs_window = Preferences()
        PanedBrowser.__prefs_window.present()

    def fill(self, songs):
        if self.__save: self.save()
        self.emit('songs-selected', list(songs), None)

browsers = [(3, _("_Paned Browser"), PanedBrowser, True)]
