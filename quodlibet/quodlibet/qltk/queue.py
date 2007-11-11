# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os

import gtk

from quodlibet import config
from quodlibet import const
from quodlibet import util

from quodlibet.qltk.ccb import ConfigCheckButton
from quodlibet.qltk.songlist import SongList
from quodlibet.qltk.songsmenu import SongsMenu        
from quodlibet.qltk.x import Tooltips
from quodlibet.qltk.playorder import OrderInOrder, OrderShuffle

QUEUE = os.path.join(const.USERDIR, "queue")

class QueueExpander(gtk.Expander):
    def __init__(self, menu, library, player):
        super(QueueExpander, self).__init__()
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        sw.set_shadow_type(gtk.SHADOW_IN)
        self.queue = PlayQueue(library, player)
        sw.add(self.queue)
        hb = gtk.HBox(spacing=12)

        hb2 = gtk.HBox(spacing=3)
        state = gtk.image_new_from_stock(
            gtk.STOCK_MEDIA_STOP, gtk.ICON_SIZE_MENU)
        hb2.pack_start(state)

        l = gtk.Label(_("_Queue"))
        hb2.pack_start(l)
        hb.pack_start(hb2)
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

        cb = ConfigCheckButton(
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
        self.connect_object(
            'drag-data-received', self.__drag_data_received, library)

        self.model = self.queue.model
        self.show_all()
        
        self.queue.model.connect_after('row-changed', self.__check_expand, l2)
        self.queue.model.connect_after('row-deleted', self.__update_count, l2)
        cb.hide()

        tips = Tooltips(self)
        tips.set_tip(b, _("Remove all songs from the queue"))
        self.connect_object('notify::visible', self.__visible, cb, menu, b)
        self.__update_count(self.model, None, l2)

        player.connect('song-started', self.__update_state_icon, state)
        player.connect('paused', self.__update_state_icon_pause,
                        state, gtk.STOCK_MEDIA_PAUSE)
        player.connect('unpaused', self.__update_state_icon_pause,
                        state, gtk.STOCK_MEDIA_PLAY)

    def __update_state_icon(self, player, song, state):
        if self.model.sourced: icon = gtk.STOCK_MEDIA_PLAY
        else: icon = gtk.STOCK_MEDIA_STOP
        state.set_from_stock(icon, gtk.ICON_SIZE_MENU)

    def __update_state_icon_pause(self, player, state, icon):
        if self.model.sourced:
            state.set_from_stock(icon, gtk.ICON_SIZE_MENU)

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
        if not self.get_property('visible'):
            self.set_expanded(False)
        self.__update_count(model, path, lab)
        self.show()

    def __drag_data_received(self, library, ctx, x, y, sel, info, etime):
        filenames = sel.data.split("\x00")
        songs = filter(None, map(library.librarian.get, filenames))
        for song in songs: self.model.append(row=[song])
        ctx.finish(bool(songs), False, etime)

    def __queue_shuffle(self, button, model):
        if not button.get_active():
            model.order = OrderInOrder(model)
        else:
            model.order = OrderShuffle(model)

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
            super(PlayQueue.CurrentColumn, self).__init__()
            self.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            self.set_fixed_width(24)

    def __init__(self, library, player):
        super(PlayQueue, self).__init__(library, player)
        self.set_size_request(-1, 120)
        self.model = self.get_model()
        self.connect('row-activated', self.__go_to, player)

        self.connect_object('popup-menu', self.__popup, library)
        self.enable_drop()
        self.connect_object('destroy', self.__write, self.model)
        self.__fill(library)

        self.connect('key-press-event', self.__delete_key_pressed)

    def __delete_key_pressed(self, widget, event):
        if (event.keyval, event.state) == gtk.accelerator_parse("Delete"):
            self.__remove(None)
            return True
        return False

    def __go_to(self, view, path, column, player):
        self.model.go_to(self.model.get_iter(path))
        player.next()

    def __fill(self, library):
        try: filenames = file(QUEUE, "rU").readlines()
        except EnvironmentError: pass
        else:
            filenames = map(str.strip, filenames)
            songs = filter(None, map(library.librarian.get, filenames))
            for song in songs:
                self.model.append([song])

    def __write(self, model):
        filenames = "\n".join([row[0]["~filename"] for row in model])
        f = file(QUEUE, "w")
        f.write(filenames)
        f.close()

    def __popup(self, library):
        songs = self.get_selected_songs()
        if not songs: return

        menu = SongsMenu(
            library, songs, queue=False, remove=False, delete=False)
        menu.preseparate()
        remove = gtk.ImageMenuItem(gtk.STOCK_REMOVE)
        remove.connect('activate', self.__remove)
        menu.prepend(remove)
        menu.show_all()
        return self.popup_menu(menu, 0, gtk.get_current_event_time())

    def __remove(self, item):
        model, paths = self.get_selection().get_selected_rows()
        if model: map(self.model.remove, map(model.get_iter, paths))

    def set_sort_by(self, *args): pass
    def get_sort_by(self, *args): return "", False
