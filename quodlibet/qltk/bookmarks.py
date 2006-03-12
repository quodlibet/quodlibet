# -*- coding: utf-8 -*-
# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

# FIXME: Only allow one bookmark window per song.

import gtk
import pango
import qltk
import util

from qltk.entry import ValidatingEntry

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

class EditBookmarks(qltk.Window):
    def __init__(self, parent, watcher, player):
        super(EditBookmarks, self).__init__()
        self.set_transient_for(qltk.get_top_parent(parent))
        self.set_border_width(12)
        self.set_default_size(350, 250)
        self.set_title(_("Bookmarks") + " - %s" % player.song.comma("title"))
        self.add(gtk.VBox(spacing=6))

        hb = gtk.HBox(spacing=12)
        time = gtk.Entry()
        time.set_width_chars(5)
        name = gtk.Entry()
        name.set_text(_("Bookmark Name"))
        add = gtk.Button(stock=gtk.STOCK_ADD)
        add.get_image().set_from_icon_name(gtk.STOCK_ADD, gtk.ICON_SIZE_MENU)
        hb.pack_start(time, expand=False)
        hb.pack_start(name)
        hb.pack_start(add)
        self.child.pack_start(hb, expand=False)

        model = gtk.ListStore(int, str)
        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw.add(gtk.TreeView(model))

        render = gtk.CellRendererText()
        def cdf(column, cell, model, iter):
            if model[iter][0] < 0: cell.set_property('text', _("N/A"))
            else: cell.set_property('text', util.format_time(model[iter][0]))
        col = gtk.TreeViewColumn(_("Time"), render)
        col.set_cell_data_func(render, cdf)
        sw.child.append_column(col)

        render = gtk.CellRendererText()
        render.set_property('ellipsize', pango.ELLIPSIZE_END)
        col = gtk.TreeViewColumn(_("Bookmark Name"), render, text=1)
        sw.child.append_column(col)
        self.child.pack_start(sw)

        hbox = gtk.HButtonBox()
        remove = gtk.Button(stock=gtk.STOCK_REMOVE)
        remove.set_sensitive(False)
        hbox.pack_start(remove)
        close = gtk.Button(stock=gtk.STOCK_CLOSE)
        close.connect_object('clicked', qltk.Window.destroy, self)
        hbox.pack_start(close)
        self.child.pack_start(hbox, expand=False)

        add.connect_object('clicked', self.__add, model, time, name)

        song = player.song
        model.connect('row-changed', self.__set_bookmarks, watcher, song)

        selection = sw.child.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        selection.connect('changed', self.__check_selection, remove)
        remove.connect('clicked', self.__remove, selection, watcher, song)

        time.connect_object('changed', self.__check_entry, add, time, name)
        name.connect_object('changed', self.__check_entry, add, time, name)
        time.set_text(util.format_time(player.get_position() // 1000))

        name.connect_object('activate', gtk.Button.clicked, add)

        s = watcher.connect('removed', self.__check_lock, song, model)
        self.connect_object('destroy', watcher.disconnect, s)

        self.__fill(model, song)
        self.show_all()
        name.grab_focus()

    def __check_lock(self, watcher, songs, song, model):
        if song in songs:
            model.clear()
            for c in self.child.get_children()[:-1]:
                c.set_sensitive(False)

    def __check_entry(self, add, time, name):
        try: t = util.parse_time(time.get_text(), None)
        except: add.set_sensitive(False)
        else: add.set_sensitive(bool(name.get_text()))

    def __add(self, model, time, name):
        try: time = util.parse_time(time.get_text(), None)
        except: pass
        else: model.append([time, name.get_text()])

    def __check_selection(self, selection, remove):
        remove.set_sensitive(bool(selection.get_selected_rows()[1]))

    def __remove(self, remove, selection, watcher, song):
        model, rows = selection.get_selected_rows()
        if model:
            map(model.remove, map(model.get_iter, rows))
            self.__set_bookmarks(model, None, None, watcher, song)

    def __set_bookmarks(self, model, a, b, watcher, song):
        try: song.bookmarks = [(r[0], r[1].decode('utf-8')) for r in model]
        except (AttributeError, ValueError): pass
        else: watcher.changed([song])

    def __fill(self, model, song):
        model.clear()
        for time, mark in song.bookmarks:
            model.append([time, mark])
