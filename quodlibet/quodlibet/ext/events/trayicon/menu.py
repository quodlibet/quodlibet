# Copyright 2004-2009 Joe Wreschnig, Michael Urman, Steven Robertson
#           2011-2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import GObject, Gtk

from quodlibet.browsers.playlists import PlaylistsBrowser
from quodlibet.browsers.playlists.menu import PlaylistMenu

from quodlibet import _
from quodlibet import browsers
from quodlibet import qltk
from quodlibet.qltk.ratingsmenu import RatingsMenuItem
from quodlibet.qltk.x import SeparatorMenuItem, MenuItem
from quodlibet.util import connect_obj, connect_destroy, is_plasma
from quodlibet.qltk import Icons
from quodlibet.qltk.browser import LibraryBrowser
from quodlibet.qltk.information import Information
from quodlibet.qltk.properties import SongProperties


class IndicatorMenu(Gtk.Menu):

    __gsignals__ = {
        'action-item-changed': (GObject.SignalFlags.RUN_LAST, None, tuple()),
    }

    def __init__(self, app, add_show_item=False):
        super(IndicatorMenu, self).__init__()

        self._app = app
        player = app.player

        show_item_bottom = is_plasma()
        if add_show_item:
            show_item = Gtk.CheckMenuItem.new_with_mnemonic(
                _("_Show %(application-name)s") % {
                    "application-name": app.name})

            def on_toggled(menuitem):
                if menuitem.get_active():
                    app.present()
                else:
                    app.hide()

            self._toggle_id = show_item.connect("toggled", on_toggled)

            def on_visible_changed(*args):
                with show_item.handler_block(self._toggle_id):
                    show_item.set_active(app.window.get_visible())

            connect_destroy(app.window, "notify::visible", on_visible_changed)
        else:
            show_item = None

        self._play_item = MenuItem(_("_Play"), Icons.MEDIA_PLAYBACK_START)
        self._play_item.connect("activate", self._on_play_pause, player)
        self._play_item.set_no_show_all(True)
        self._pause_item = MenuItem(_("P_ause"), Icons.MEDIA_PLAYBACK_PAUSE)
        self._pause_item.connect("activate", self._on_play_pause, player)
        self._pause_item.set_no_show_all(True)
        self._action_item = None

        previous = MenuItem(_("Pre_vious"), Icons.MEDIA_SKIP_BACKWARD)
        previous.connect('activate', lambda *args: player.previous(force=True))

        next = MenuItem(_("_Next"), Icons.MEDIA_SKIP_FORWARD)
        next.connect('activate', lambda *args: player.next())

        player_options = app.player_options

        shuffle = Gtk.CheckMenuItem(label=_("_Shuffle"), use_underline=True)
        player_options.bind_property("shuffle", shuffle, "active",
                                     GObject.BindingFlags.BIDIRECTIONAL)
        player_options.notify("shuffle")

        repeat = Gtk.CheckMenuItem(label=_("_Repeat"), use_underline=True)
        player_options.bind_property("repeat", repeat, "active",
                                     GObject.BindingFlags.BIDIRECTIONAL)
        player_options.notify("repeat")

        safter = Gtk.CheckMenuItem(label=_("Stop _After This Song"),
                                   use_underline=True)
        player_options.bind_property("stop-after", safter, "active",
                                     GObject.BindingFlags.BIDIRECTIONAL)
        player_options.notify("stop-after")

        browse = qltk.MenuItem(_("Open _Browser"), Icons.EDIT_FIND)
        browse_sub = Gtk.Menu()

        for Kind in browsers.browsers:
            i = Gtk.MenuItem(label=Kind.accelerated_name, use_underline=True)
            connect_obj(i,
                'activate', LibraryBrowser.open, Kind, app.library, app.player)
            browse_sub.append(i)

        browse.set_submenu(browse_sub)

        self._props = qltk.MenuItem(_("Edit _Tags"), Icons.EDIT)

        def on_properties(*args):
            song = player.song
            window = SongProperties(app.librarian, [song])
            window.show()

        self._props.connect('activate', on_properties)

        self._info = MenuItem(_("_Information"), Icons.DIALOG_INFORMATION)

        self._playlists_item = MenuItem(_("Play_lists"),
                                        Icons.FOLDER_DRAG_ACCEPT)
        self._new_playlist_submenu_for(player.song)

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

        if not show_item_bottom and show_item:
            self.append(show_item)
            self.append(SeparatorMenuItem())

        self.append(self._play_item)
        self.append(self._pause_item)
        self.append(previous)
        self.append(next)
        self.append(SeparatorMenuItem())
        self.append(shuffle)
        self.append(repeat)
        self.append(safter)
        self.append(SeparatorMenuItem())
        self.append(rating)
        self.append(self._playlists_item)
        self.append(self._props)
        self.append(self._info)
        self.append(SeparatorMenuItem())
        self.append(browse)
        self.append(SeparatorMenuItem())
        self.append(quit)

        if show_item_bottom and show_item:
            self.append(SeparatorMenuItem())
            self.append(show_item)

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
        self._new_playlist_submenu_for(song)

    def _new_playlist_submenu_for(self, song):
        submenu = self._playlists_item.get_submenu()
        if submenu:
            submenu.destroy()
        playlist_menu = PlaylistMenu([song], PlaylistsBrowser.playlists())

        def on_new(widget, playlist):
            PlaylistsBrowser.changed(playlist)
        playlist_menu.connect('new', on_new)
        self._playlists_item.set_submenu(playlist_menu)
        self._playlists_item.set_sensitive(bool(song) and song.can_add)
        self._playlists_item.show_all()

    def _on_play_pause(self, menuitem, player):
        player.playpause()
