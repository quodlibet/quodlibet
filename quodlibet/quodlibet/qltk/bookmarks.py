# -*- coding: utf-8 -*-
# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

# FIXME: Only allow one bookmark window per song.

import gtk
import pango

from quodlibet import qltk
from quodlibet import util

from quodlibet.qltk.views import RCMHintedTreeView

def MenuItems(marks, player, seekable):
    sizes = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
    items = []
    if not marks or marks[0][0] != 0:
        # Translators: Refers to the beginning of the playing song.
        marks.insert(0, (0, _("Beginning")))
    for time, mark in marks:
        i = gtk.MenuItem()
        i.connect_object('activate', player.seek, time * 1000)
        i.set_sensitive(time >= 0 and seekable)
        i.add(gtk.HBox(spacing=12))
        if time < 0: l = gtk.Label(_("N/A"))
        else: l = gtk.Label(util.format_time(time))
        l.set_alignment(0.0, 0.5)
        sizes.add_widget(l)
        i.child.pack_start(l, expand=False)
        m = gtk.Label(mark)
        m.set_alignment(0.0, 0.5)
        i.child.pack_start(m)
        i.show_all()
        items.append(i)
    return items

class EditBookmarksPane(gtk.VBox):
    def __init__(self, library, song, close=False):
        super(EditBookmarksPane, self).__init__(spacing=6)

        hb = gtk.HBox(spacing=12)
        self.time = time = gtk.Entry()
        time.set_width_chars(5)
        self.markname = name = gtk.Entry()
        add = gtk.Button(stock=gtk.STOCK_ADD)
        add.get_image().set_from_icon_name(gtk.STOCK_ADD, gtk.ICON_SIZE_MENU)
        hb.pack_start(time, expand=False)
        hb.pack_start(name)
        hb.pack_start(add, expand=False)
        self.pack_start(hb, expand=False)

        model = gtk.ListStore(int, str)
        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw.add(RCMHintedTreeView(model))

        render = gtk.CellRendererText()
        def cdf(column, cell, model, iter):
            if model[iter][0] < 0: cell.set_property('text', _("N/A"))
            else: cell.set_property('text', util.format_time(model[iter][0]))
        render.set_property('editable', True)
        render.connect('edited', self.__edit_time, model)
        col = gtk.TreeViewColumn(_("Time"), render)
        col.set_cell_data_func(render, cdf)
        sw.child.append_column(col)

        render = gtk.CellRendererText()
        render.set_property('ellipsize', pango.ELLIPSIZE_END)
        col = gtk.TreeViewColumn(_("Bookmark Name"), render, text=1)
        render.set_property('editable', True)
        render.connect('edited', self.__edit_name, model)
        sw.child.append_column(col)
        self.pack_start(sw)
        self.accels = gtk.AccelGroup()

        hbox = gtk.HButtonBox()
        remove = gtk.Button(stock=gtk.STOCK_REMOVE)
        remove.set_sensitive(False)
        hbox.pack_start(remove)
        if close:
            self.close = gtk.Button(stock=gtk.STOCK_CLOSE)
            hbox.pack_start(self.close)
        else: hbox.set_layout(gtk.BUTTONBOX_END)
        self.pack_start(hbox, expand=False)

        add.connect_object('clicked', self.__add, model, time, name)

        model.set_sort_column_id(0, gtk.SORT_ASCENDING)
        model.connect('row-changed', self.__set_bookmarks, library, song)

        selection = sw.child.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        selection.connect('changed', self.__check_selection, remove)
        remove.connect('clicked', self.__remove, selection, library, song)

        time.connect_object('changed', self.__check_entry, add, time, name)
        name.connect_object('changed', self.__check_entry, add, time, name)
        name.connect_object('activate', gtk.Button.clicked, add)

        time.set_text(_("MM:SS"))
        time.connect_object('activate', gtk.Entry.grab_focus, name)
        name.set_text(_("Bookmark Name"))

        menu = gtk.Menu()
        remove = gtk.ImageMenuItem(gtk.STOCK_REMOVE)
        remove.connect('activate', self.__remove, selection, library, song)
        keyval, mod = gtk.accelerator_parse("Delete")
        remove.add_accelerator(
            'activate', self.accels, keyval, mod, gtk.ACCEL_VISIBLE)
        menu.append(remove)
        menu.show_all()
        sw.child.connect('popup-menu', self.__popup, menu)
        sw.child.connect('key-press-event', self.__view_key_press, remove)
        self.connect_object('destroy', gtk.Menu.destroy, menu)

        self.__fill(model, song)

    def __view_key_press(self, view, event, remove):
        if event.keyval == gtk.accelerator_parse("Delete")[0]:
            remove.activate()

    def __popup(self, view, menu):
        return view.popup_menu(menu, 0, gtk.get_current_event_time())

    def __edit_name(self, render, path, new, model):
        if new: model[path][1] = new

    def __edit_time(self, render, path, new, model):
        try: time = util.parse_time(new, None)
        except: pass
        else: model[path][0] = time

    def __check_entry(self, add, time, name):
        try: util.parse_time(time.get_text(), None)
        except: add.set_sensitive(False)
        else: add.set_sensitive(bool(name.get_text()))

    def __add(self, model, time, name):
        try: time = util.parse_time(time.get_text(), None)
        except: pass
        else: model.append([time, name.get_text()])

    def __check_selection(self, selection, remove):
        remove.set_sensitive(bool(selection.get_selected_rows()[1]))

    def __remove(self, remove, selection, library, song):
        model, rows = selection.get_selected_rows()
        if model:
            map(model.remove, map(model.get_iter, rows))
            self.__set_bookmarks(model, None, None, library, song)

    def __set_bookmarks(self, model, a, b, library, song):
        try: song.bookmarks = [(r[0], r[1].decode('utf-8')) for r in model]
        except (AttributeError, ValueError): pass
        else:
            if library is not None:
                library.changed([song])

    def __fill(self, model, song):
        model.clear()
        for time, mark in song.bookmarks:
            model.append([time, mark])

class EditBookmarks(qltk.Window):
    def __init__(self, parent, library, player):
        super(EditBookmarks, self).__init__()
        self.set_transient_for(qltk.get_top_parent(parent))
        self.set_border_width(12)
        self.set_default_size(350, 250)
        self.set_title(_("Bookmarks") + " - %s" % player.song.comma("title"))

        self.add(EditBookmarksPane(library, player.song, close=True))

        s = library.connect('removed', self.__check_lock, player.song)
        self.connect_object('destroy', library.disconnect, s)

        position = player.get_position() // 1000
        self.child.time.set_text(util.format_time(position))
        self.child.markname.grab_focus()

        self.child.close.connect_object('clicked', qltk.Window.destroy, self)

        self.show_all()

    def __check_lock(self, library, songs, song, model):
        if song in songs:
            for c in self.child.get_children()[:-1]:
                c.set_sensitive(False)
