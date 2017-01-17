# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#                2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

from gi.repository import Gtk, Gdk

import quodlibet
from quodlibet import ngettext, _
from quodlibet import config
from quodlibet import util
from quodlibet import qltk

from quodlibet.util import connect_obj, connect_destroy, format_time_preferred
from quodlibet.qltk import Icons, gtk_version, add_css
from quodlibet.qltk.ccb import ConfigCheckButton
from quodlibet.qltk.songlist import SongList, DND_QL, DND_URI_LIST
from quodlibet.qltk.songsmenu import SongsMenu
from quodlibet.qltk.songmodel import PlaylistModel
from quodlibet.qltk.playorder import OrderInOrder, OrderShuffle
from quodlibet.qltk.x import ScrolledWindow, SymbolicIconImage, \
    SmallImageButton, MenuItem

QUEUE = os.path.join(quodlibet.get_user_dir(), "queue")


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


class ExpandBoxHack(Gtk.HBox):

    def do_get_preferred_width(self):
        # Workaround for https://bugzilla.gnome.org/show_bug.cgi?id=765602
        # set_label_fill() no longer works since 3.20. Fake a natural size
        # which is larger than the expander can be to force the parent to
        # allocate to us the whole space.
        min_, nat = Gtk.HBox.do_get_preferred_width(self)
        if gtk_version > (3, 19):
            # if we get too large gtk calcs will overflow..
            nat = max(nat, 2 ** 16)
        return (min_, nat)


class QueueExpander(Gtk.Expander):

    def __init__(self, library, player):
        super(QueueExpander, self).__init__(spacing=3)
        sw = ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.set_shadow_type(Gtk.ShadowType.IN)
        self.queue = PlayQueue(library, player)
        self.queue.props.expand = True
        sw.add(self.queue)

        add_css(self, ".ql-expanded title { margin-bottom: 5px; }")

        outer = ExpandBoxHack(spacing=12)

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
            image=SymbolicIconImage(Icons.EDIT_CLEAR, Gtk.IconSize.MENU))
        b.set_tooltip_text(_("Remove all songs from the queue"))
        b.connect('clicked', self.__clear_queue)
        b.set_no_show_all(True)
        b.set_relief(Gtk.ReliefStyle.NONE)
        left.pack_start(b, False, False, 0)

        self.count_label = count_label = Gtk.Label()
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
        cb.set_no_show_all(True)
        left.pack_start(cb, False, True, 0)

        self.set_label_widget(outer)
        self.add(sw)
        connect_obj(self, 'notify::expanded', self.__expand, cb, b)

        targets = [
            ("text/x-quodlibet-songs", Gtk.TargetFlags.SAME_APP, DND_QL),
            ("text/uri-list", 0, DND_URI_LIST)
        ]
        targets = [Gtk.TargetEntry.new(*t) for t in targets]

        self.drag_dest_set(Gtk.DestDefaults.ALL, targets, Gdk.DragAction.COPY)
        self.connect('drag-motion', self.__motion)
        self.connect('drag-data-received', self.__drag_data_received)

        self.queue.model.connect_after('row-inserted',
            util.DeferredSignal(self.__check_expand), count_label)
        self.queue.model.connect_after('row-deleted',
            util.DeferredSignal(self.__update_count), count_label)

        connect_obj(self, 'notify::visible', self.__visible, cb, b)
        self.__update_count(self.model, None, count_label)

        connect_destroy(
            player, 'song-started', self.__update_state_icon, state_icon)
        connect_destroy(
            player, 'paused', self.__update_state_icon_pause,
            state_icon, True)
        connect_destroy(
            player, 'unpaused', self.__update_state_icon_pause,
            state_icon, False)

        # to make the children clickable if mapped
        # ....no idea why, but works
        def hack(expander):
            label = expander.get_label_widget()
            if label:
                label.unmap()
                label.map()
        self.connect("map", hack)

        self.set_expanded(config.getboolean("memory", "queue_expanded"))
        self.notify("expanded")

        for child in self.get_children():
            child.show_all()

    @property
    def model(self):
        return self.queue.model

    def refresh(self):
        self.__update_count(self.model, None, self.count_label)

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
                "count": len(model), "time": format_time_preferred(time)}
        lab.set_text(text)

    def __check_expand(self, model, path, iter, lab):
        self.__update_count(model, path, lab)
        self.show()

    def __drag_data_received(self, expander, *args):
        self.queue.emit('drag-data-received', *args)

    def __queue_shuffle(self, button, model):
        model.order = OrderShuffle() if button.get_active() else OrderInOrder()

    def __expand(self, cb, prop, clear):
        expanded = self.get_expanded()

        style_context = self.get_style_context()
        if expanded:
            style_context.add_class("ql-expanded")
        else:
            style_context.remove_class("ql-expanded")

        cb.set_property('visible', expanded)
        clear.set_property('visible', expanded)
        config.set("memory", "queue_expanded", str(expanded))

    def __visible(self, cb, prop, clear):
        value = self.get_property('visible')
        config.set("memory", "queue", str(value))


class QueueModel(PlaylistModel):
    """Own class for debugging"""


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
        super(PlayQueue, self).__init__(library, player, model_cls=QueueModel)
        self.set_size_request(-1, 120)
        self.connect('row-activated', self.__go_to, player)

        connect_obj(self, 'popup-menu', self.__popup, library)
        self.enable_drop()
        connect_obj(self, 'destroy', self.__write, self.model)
        self.__fill(library)

        self.connect('key-press-event', self.__delete_key_pressed)

    def __delete_key_pressed(self, widget, event):
        if qltk.is_accel(event, "Delete"):
            self.__remove()
            return True
        return False

    def __go_to(self, view, path, column, player):
        if player.go_to(self.model.get_iter(path), explicit=True,
                        source=self.model):
            player.paused = False

    def __fill(self, library):
        try:
            with open(QUEUE, "rU") as f:
                filenames = f.readlines()
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
        with open(QUEUE, "w") as f:
            f.write(filenames)

    def __popup(self, library):
        songs = self.get_selected_songs()
        if not songs:
            return

        menu = SongsMenu(
            library, songs, queue=False, remove=False, delete=False,
            ratings=False)
        menu.preseparate()
        remove = MenuItem(_("_Remove"), Icons.LIST_REMOVE)
        qltk.add_fake_accel(remove, "Delete")
        remove.connect('activate', self.__remove)
        menu.prepend(remove)
        menu.show_all()
        return self.popup_menu(menu, 0, Gtk.get_current_event_time())

    def __remove(self, *args):
        self.remove_selection()
