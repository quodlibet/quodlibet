# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

from gi.repository import Gtk, Gdk, Gio

from quodlibet import config
from quodlibet import const
from quodlibet import util
from quodlibet import qltk

from quodlibet.qltk.ccb import ConfigCheckButton
from quodlibet.qltk.songlist import SongList, DND_QL, DND_URI_LIST
from quodlibet.qltk.songsmenu import SongsMenu
from quodlibet.qltk.playorder import OrderInOrder, OrderShuffle
from quodlibet.qltk.x import ScrolledWindow, SymbolicIconImage, \
    SmallImageButton

QUEUE = os.path.join(const.USERDIR, "queue")


class PlaybackStatusIcon(Gtk.Box):
    """A widget showing a play/pause/stop symbolic icon"""

    def __init__(self):
        super(PlaybackStatusIcon, self).__init__()
        self._icons = {}

    def _set(self, name):
        if name not in self._icons:
            image = SymbolicIconImage(name, Gtk.IconSize.MENU)
            self._icons[name] = image
            image.show()
        else:
            image = self._icons[name]

        children = self.get_children()
        if children:
            self.remove(children[0])
        self.add(image)

    def play(self):
        self._set("media-playback-start")

    def stop(self):
        self._set("media-playback-stop")

    def pause(self):
        self._set("media-playback-pause")


class QueueExpander(Gtk.Expander):
    def __init__(self, menu, library, player):
        super(QueueExpander, self).__init__()
        sw = ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.set_shadow_type(Gtk.ShadowType.IN)
        self.queue = PlayQueue(library, player)
        sw.add(self.queue)

        outer = Gtk.HBox(spacing=12)

        left = Gtk.HBox(spacing=12)

        hb2 = Gtk.HBox(spacing=3)
        state_icon = PlaybackStatusIcon()
        state_icon.stop()
        state_icon.show()
        hb2.pack_start(state_icon, True, True, 0)
        name_label = Gtk.Label(label=_("_Queue"), use_underline=True)
        hb2.pack_start(name_label, True, True, 0)
        left.pack_start(hb2, False, True, 0)

        b = SmallImageButton(
            image=Gtk.Image.new_from_stock(Gtk.STOCK_CLEAR, Gtk.IconSize.MENU))
        b.set_tooltip_text(_("Remove all songs from the queue"))
        b.connect('clicked', self.__clear_queue)
        b.hide()
        b.set_relief(Gtk.ReliefStyle.NONE)
        left.pack_start(b, False, False, 0)

        count_label = Gtk.Label()
        left.pack_start(count_label, False, True, 0)

        outer.pack_start(left, True, True, 0)

        close_button = SmallImageButton(
            image=SymbolicIconImage("window-close", Gtk.IconSize.MENU),
            relief=Gtk.ReliefStyle.NONE)

        close_button.connect("clicked", lambda *x: self.hide())

        outer.pack_start(close_button, False, False, 6)
        self.set_label_fill(True)

        cb = ConfigCheckButton(
            _("_Random"), "memory", "shufflequeue")
        cb.connect('toggled', self.__queue_shuffle, self.queue.model)
        cb.set_active(config.getboolean("memory", "shufflequeue"))
        left.pack_start(cb, False, True, 0)

        self.set_label_widget(outer)
        self.add(sw)
        self.connect_object('notify::expanded', self.__expand, cb, b)

        targets = [
            ("text/x-quodlibet-songs", Gtk.TargetFlags.SAME_APP, DND_QL),
            ("text/uri-list", 0, DND_URI_LIST)
        ]
        targets = [Gtk.TargetEntry.new(*t) for t in targets]

        self.drag_dest_set(Gtk.DestDefaults.ALL, targets, Gdk.DragAction.COPY)
        self.connect('drag-motion', self.__motion)
        self.connect('drag-data-received', self.__drag_data_received)

        self.show_all()

        self.queue.model.connect_after('row-inserted',
            util.DeferredSignal(self.__check_expand), count_label)
        self.queue.model.connect_after('row-deleted',
            util.DeferredSignal(self.__update_count), count_label)
        cb.hide()

        self.connect_object('notify::visible', self.__visible, cb, menu, b)
        self.__update_count(self.model, None, count_label)

        player.connect('song-started', self.__update_state_icon, state_icon)
        player.connect('paused', self.__update_state_icon_pause,
                        state_icon, True)
        player.connect('unpaused', self.__update_state_icon_pause,
                        state_icon, False)

        # to make the children clickable if mapped
        # ....no idea why, but works
        def hack(expander):
            label = expander.get_label_widget()
            if label:
                label.unmap()
                label.map()
        self.connect("map", hack)

    @property
    def model(self):
        return self.queue.model

    def __update_state_icon(self, player, song, state_icon):
        if self.model.sourced:
            state_icon.play()
        else:
            state_icon.stop()

    def __update_state_icon_pause(self, player, state_icon, paused):
        if self.model.sourced:
            if paused:
                state_icon.pause()
            else:
                state_icon.play()
        else:
            state_icon.stop()

    def __clear_queue(self, activator):
        self.model.clear()

    def __motion(self, wid, context, x, y, time):
        Gdk.drag_status(context, Gdk.DragAction.COPY, time)
        return True

    def __update_count(self, model, path, lab):
        if len(model) == 0:
            text = ""
        else:
            time = sum([row[0].get("~#length", 0) for row in model])
            text = ngettext("%(count)d song (%(time)s)",
                            "%(count)d songs (%(time)s)",
                            len(model)) % {
                "count": len(model), "time": util.format_time(time)}
        lab.set_text(text)

    def __check_expand(self, model, path, iter, lab):
        if not self.get_property('visible'):
            self.set_expanded(False)
        self.__update_count(model, path, lab)
        self.show()

    def __drag_data_received(self, expander, *args):
        self.queue.emit('drag-data-received', *args)

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

    sortable = False

    class CurrentColumn(Gtk.TreeViewColumn):
        # Match MainSongList column sizes by default.
        header_name = "~current"

        def __init__(self):
            super(PlayQueue.CurrentColumn, self).__init__()
            self.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            self.set_fixed_width(24)

    def __init__(self, library, player):
        super(PlayQueue, self).__init__(library, player)
        self.set_size_request(-1, 120)
        self.connect('row-activated', self.__go_to, player)

        self.connect_object('popup-menu', self.__popup, library)
        self.enable_drop()
        self.connect_object('destroy', self.__write, self.model)
        self.__fill(library)

        self.connect('key-press-event', self.__delete_key_pressed)

    def __delete_key_pressed(self, widget, event):
        if qltk.is_accel(event, "Delete"):
            self.__remove()
            return True
        return False

    def __go_to(self, view, path, column, player):
        self.model.go_to(self.model.get_iter(path))
        player.next()

    def __fill(self, library):
        try:
            filenames = file(QUEUE, "rU").readlines()
        except EnvironmentError:
            pass
        else:
            filenames = map(str.strip, filenames)
            if library.librarian:
                library = library.librarian
            songs = filter(None, map(library.get, filenames))
            for song in songs:
                self.model.append([song])

    def __write(self, model):
        filenames = "\n".join([row[0]["~filename"] for row in model])
        f = file(QUEUE, "w")
        f.write(filenames)
        f.close()

    def __popup(self, library):
        songs = self.get_selected_songs()
        if not songs:
            return

        menu = SongsMenu(
            library, songs, queue=False, remove=False, delete=False,
            parent=self)
        menu.preseparate()
        remove = Gtk.ImageMenuItem(Gtk.STOCK_REMOVE, use_stock=True)
        qltk.add_fake_accel(remove, "Delete")
        remove.connect('activate', self.__remove)
        menu.prepend(remove)
        menu.show_all()
        return self.popup_menu(menu, 0, Gtk.get_current_event_time())

    def __remove(self, *args):
        self.remove_selection()
