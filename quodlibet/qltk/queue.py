# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gtk
import const
import config
import qltk
import util
from qltk.songlist import SongList
from library import library

class QueueExpander(gtk.Expander):
    def __init__(self, menu, watcher):
        gtk.Expander.__init__(self)
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        sw.set_shadow_type(gtk.SHADOW_IN)
        self.queue = PlayQueue(watcher)
        sw.add(self.queue)
        hb = gtk.HBox(spacing=12)
        l = gtk.Label(_("_Queue"))
        hb.pack_start(l)
        l.set_use_underline(True)

        clear = gtk.image_new_from_stock(gtk.STOCK_CLEAR, gtk.ICON_SIZE_MENU)
        b = gtk.Button()
        b.add(clear)
        b.connect('clicked', self.__clear_queue)
        b.hide()
        b.set_relief(gtk.RELIEF_NONE)
        hb.pack_start(b, expand=False, fill=False)

        l2 = gtk.Label()
        hb.pack_start(l2)

        cb = qltk.ConfigCheckButton(
            _("_Random"), "memory", "shufflequeue")
        cb.connect('toggled', self.__queue_shuffle, self.queue.model)
        cb.set_active(config.getboolean("memory", "shufflequeue"))
        hb.pack_start(cb)

        self.set_label_widget(hb)
        self.add(sw)
        self.connect_object('notify::expanded', self.__expand, cb, b)

        targets = [("text/x-quodlibet-songs", gtk.TARGET_SAME_APP, 1)]
        self.drag_dest_set(
            gtk.DEST_DEFAULT_ALL, targets, gtk.gdk.ACTION_COPY)
        self.connect('drag-motion', self.__motion)
        self.connect('drag-data-received', self.__drag_data_received)

        self.model = self.queue.model
        self.show_all()
        
        self.queue.model.connect_after('row-changed', self.__check_expand, l2)
        self.queue.model.connect_after('row-deleted', self.__update_count, l2)
        cb.hide()

        tips = gtk.Tooltips()
        tips.set_tip(b, _("Remove all songs from the queue"))
        tips.enable()
        self.connect_object('destroy', gtk.Tooltips.destroy, tips)
        self.connect_object('notify::visible', self.__visible, cb, menu, b)
        self.__update_count(self.model, None, l2)

    def __clear_queue(self, activator):
        self.model.clear()

    def __motion(self, wid, context, x, y, time):
        context.drag_status(gtk.gdk.ACTION_COPY, time)
        return True

    def __update_count(self, model, path, lab):
        if len(model) == 0: text = ""
        else:
            time = sum([row[0].get("~#length", 0) for row in model])
            text = ngettext("%(count)d song (%(time)s)",
                            "%(count)d songs (%(time)s)",
                            len(model)) % {
                "count": len(model), "time": util.format_time(time) }
        lab.set_text(text)

    def __check_expand(self, model, path, iter, lab):
        # Interfere as little as possible with the current size.
        if not self.get_property('visible'): self.set_expanded(False)
        self.__update_count(model, path, lab)
        self.show()

    def __drag_data_received(self, qex, ctx, x, y, sel, info, etime):
        filenames = sel.data.split("\x00")
        songs = filter(None, map(library.get, filenames))
        for song in songs: self.model.append(row=[song])
        ctx.finish(bool(songs), False, etime)

    def __queue_shuffle(self, button, model):
        model.order = button.get_active()

    def __expand(self, cb, prop, clear):
        cb.set_property('visible', self.get_expanded())
        clear.set_property('visible', self.get_expanded())

    def __visible(self, cb, prop, menu, clear):
        value = self.get_property('visible')
        config.set("memory", "queue", str(value))
        menu.set_active(value)
        self.set_expanded(not self.model.is_empty())
        cb.set_property('visible', self.get_expanded())
        clear.set_property('visible', self.get_expanded())

class PlayQueue(SongList):
    class CurrentColumn(gtk.TreeViewColumn):
        # Match MainSongList column sizes by default.
        header_name = "~current"
        def __init__(self):
            gtk.TreeViewColumn.__init__(self)
            self.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            self.set_fixed_width(24)

    def __init__(self, watcher):
        super(PlayQueue, self).__init__(watcher)
        self.set_size_request(-1, 120)
        self.model = self.get_model()
        menu = gtk.Menu()
        rem = gtk.ImageMenuItem(gtk.STOCK_REMOVE)
        rem.connect('activate', self.__remove)
        props = gtk.ImageMenuItem(gtk.STOCK_PROPERTIES)
        props.connect_object('activate', self.__properties, watcher)
        menu.append(rem); menu.append(props); menu.show_all()
        self.connect_object('button-press-event', self.__button_press, menu)
        self.connect_object('popup-menu', self.__popup, menu)
        self.enable_drop()
        self.connect('destroy', self.__write)
        self.__fill()

    def __fill(self):
        try: filenames = file(const.QUEUE, "rU").readlines()
        except EnvironmentError: pass
        else:
            for fn in map(str.strip, filenames):
                if fn in library:
                    self.model.append([library[fn]])

    def __write(self, *args):
        filenames = "\n".join([row[0]["~filename"] for row in self.model])
        f = file(const.QUEUE, "w")
        f.write(filenames)
        f.close()

    def __popup(self, menu):
        menu.popup(None, None, None, 3, 0)
        return True

    def __properties(self, watcher):
        SongProperties(self.get_selected_songs(), watcher)

    def __remove(self, item):
        map(self.model.remove, self.songs_to_iters(self.get_selected_songs()))

    def __button_press(self, menu, event):
        x, y = map(int, [event.x, event.y])
        try: path, col, cellx, celly = self.get_path_at_pos(x, y)
        except TypeError: return True
        self.grab_focus()
        selection = self.get_selection()
        if event.button == 3:
            if not selection.path_is_selected(path):
                self.set_cursor(path, col, 0)
            menu.popup(None, None, None, event.button, event.time)
            return True

    def set_sort_by(self, *args): pass
    def get_sort_by(self, *args): return "", False
