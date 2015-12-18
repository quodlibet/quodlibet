# -*- coding: utf-8 -*-
# Copyright 2004-2009 Joe Wreschnig, Michael Urman, Steven Robertson
#           2011,2013 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import GObject, Gtk

from quodlibet import browsers
from quodlibet import qltk
from quodlibet.qltk.ratingsmenu import RatingsMenuItem
from quodlibet.qltk.x import RadioMenuItem, SeparatorMenuItem, MenuItem
from quodlibet.util import connect_obj, connect_destroy
from quodlibet.qltk import Icons
from quodlibet.qltk.playorder import ORDERS
from quodlibet.qltk.browser import LibraryBrowser
from quodlibet.qltk.information import Information
from quodlibet.qltk.properties import SongProperties

from .util import pconfig


class IndicatorMenu(Gtk.Menu):

    __gsignals__ = {
        'action-item-changed': (GObject.SignalFlags.RUN_LAST, None, tuple()),
    }

    def __init__(self, app, add_show_item=False):
        super(IndicatorMenu, self).__init__()

        self._app = app
        player = app.player
        window = app.window

        if add_show_item:
            show_item = Gtk.CheckMenuItem.new_with_mnemonic(
                _("_Show %(application-name)s") % {
                    "application-name": app.name})

            def on_toggled(menuitem):
                app.window.set_visible(menuitem.get_active())
                pconfig.set("window_visible", menuitem.get_active())

            self._toggle_id = show_item.connect("toggled", on_toggled)

            def on_visible_changed(*args):
                with show_item.handler_block(self._toggle_id):
                    show_item.set_active(app.window.get_visible())

            connect_destroy(app.window, "notify::visible", on_visible_changed)
        else:
            show_item = None

        self._play_item = MenuItem(_("_Play"), Icons.MEDIA_PLAYBACK_START)
        self._play_item.connect("activate", self._on_play_pause, player)
        self._pause_item = MenuItem(_("P_ause"), Icons.MEDIA_PLAYBACK_PAUSE)
        self._pause_item.connect("activate", self._on_play_pause, player)
        self._action_item = None

        previous = MenuItem(_("Pre_vious"), Icons.MEDIA_SKIP_BACKWARD)
        previous.connect('activate', lambda *args: player.previous(force=True))

        next = MenuItem(_("_Next"), Icons.MEDIA_SKIP_FORWARD)
        next.connect('activate', lambda *args: player.next())

        # FIXME: the order/repeat items should depend on the player state..
        orders = Gtk.MenuItem(label=_("Play _Order"), use_underline=True)

        repeat = Gtk.CheckMenuItem(label=_("_Repeat"), use_underline=True)
        repeat.set_active(window.repeat.get_active())
        repeat.connect('toggled',
            lambda s: window.repeat.set_active(s.get_active()))

        def set_safter(widget, safter_action):
            safter_action.set_active(widget.get_active())

        safter_action = app.window.stop_after
        safter = Gtk.CheckMenuItem(label=_("Stop _after this song"),
                                   use_underline=True)
        safter.set_active(safter_action.get_active())
        safter.connect('toggled', set_safter, safter_action)

        def set_order(widget, order):
            name = order.name
            try:
                window.order.set_active_by_name(name)
            except ValueError:
                pass

        order_items = []
        item = None
        active_order = window.order.get_active()
        for Kind in ORDERS:
            item = RadioMenuItem(
                    group=item,
                    label=Kind.accelerated_name,
                    use_underline=True)
            order_items.append(item)
            if Kind is active_order:
                item.set_active(True)
            item.connect('toggled', set_order, Kind)

        order_sub = Gtk.Menu()
        order_sub.append(repeat)
        order_sub.append(safter)
        order_sub.append(SeparatorMenuItem())
        for item in order_items:
            order_sub.append(item)
        orders.set_submenu(order_sub)

        browse = qltk.MenuItem(_("_Browse Library"), Icons.EDIT_FIND)
        browse_sub = Gtk.Menu()

        for Kind in browsers.browsers:
            if Kind.is_empty:
                continue
            i = Gtk.MenuItem(label=Kind.accelerated_name, use_underline=True)
            connect_obj(i,
                'activate', LibraryBrowser.open, Kind, app.library, app.player)
            browse_sub.append(i)

        browse.set_submenu(browse_sub)

        self._props = qltk.MenuItem(_("Edit _Tags"), Icons.DOCUMENT_PROPERTIES)

        def on_properties(*args):
            song = player.song
            window = SongProperties(app.librarian, [song])
            window.show()

        self._props.connect('activate', on_properties)

        self._info = MenuItem(_("_Information"), Icons.DIALOG_INFORMATION)

        def on_information(*args):
            song = player.song
            window = Information(app.librarian, [song])
            window.show()

        self._info.connect('activate', on_information)

        def set_rating(value):
            song = player.song
            song["~#rating"] = value
            app.librarian.changed([song])

        self._rating_item = rating = RatingsMenuItem([], app.library)

        quit = MenuItem(_("_Quit"), Icons.APPLICATION_EXIT)
        quit.connect('activate', lambda *x: app.quit())

        if show_item:
            self.append(show_item)
            self.append(SeparatorMenuItem())

        self.append(self._play_item)
        self.append(self._pause_item)
        self.append(SeparatorMenuItem())
        self.append(previous)
        self.append(next)
        self.append(orders)
        self.append(SeparatorMenuItem())
        self.append(browse)
        self.append(SeparatorMenuItem())
        self.append(self._props)
        self.append(self._info)
        self.append(rating)
        self.append(SeparatorMenuItem())
        self.append(quit)

        self.show_all()

        self.set_paused(True)
        self.set_song(None)

    def get_action_item(self):
        """Returns the 'Play' or 'Pause' action menu item (used for unity).
        'action-item-changed' gets emitted if this changes.
        """

        return self._action_item

    def set_paused(self, paused):
        """Update the menu based on the player paused state"""

        self._play_item.set_visible(paused)
        self._pause_item.set_visible(not paused)
        self._action_item = self._play_item if paused else self._pause_item
        self.emit("action-item-changed")

    def set_song(self, song):
        """Update the menu based on the passed song. Can be None.

        This should be the persistent song and not a stream/info one.
        """

        self._rating_item.set_sensitive(song is not None)
        self._info.set_sensitive(song is not None)
        self._props.set_sensitive(song is not None)
        self._rating_item.set_songs([song])

    def _on_play_pause(self, menuitem, player):
        if player.song:
            player.paused ^= True
        else:
            player.reset()
