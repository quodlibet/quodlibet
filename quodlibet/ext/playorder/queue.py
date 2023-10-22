# Copyright 2009 Steven Robertson
#        2016-20 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import _
from quodlibet import app
from quodlibet import config
from quodlibet import qltk
from quodlibet.plugins.playorder import ShufflePlugin
from quodlibet.qltk.ccb import ConfigCheckButton
from quodlibet.qltk import Icons
from quodlibet.qltk.playorder import OrderInOrder

from gi.repository import Gtk


class QueueOrder(ShufflePlugin, OrderInOrder):
    PLUGIN_ID = "queue"
    PLUGIN_NAME = _("Queue Only")
    PLUGIN_ICON = Icons.VIEW_LIST
    PLUGIN_DESC = _("Limits playing of songs to the queue.\n\n"
                    "Select this play order in the main window, "
                    "then double-clicking any song will enqueue it "
                    "instead of playing.")
    display_name = _("Queue only")
    accelerated_name = _("_Queue only")

    def PluginPreferences(self):
        box = Gtk.HBox()
        ccb = ConfigCheckButton(_("Automatically start playing "
                                  "double-clicked songs"),
                                "plugins", "queue_only_autoplay")
        autoplay = config.getboolean("plugins", "queue_only_autoplay", False)
        ccb.set_active(autoplay)
        box.pack_start(qltk.Frame(_("Preferences"), child=ccb), True, True, 0)
        return box

    def next(self, playlist, iter):
        return None

    def set_explicit(self, playlist, iter):
        if iter is None:
            return
        song = playlist[iter][0]
        if song is None:
            return

        # store queue size for jumping to newly added items
        queue = app.window.playlist.q
        queue_size = len(queue)

        app.window.playlist.enqueue([playlist[iter][0]])

        # if setting enabled, start playing the first added song
        autoplay = config.getboolean("plugins", "queue_only_autoplay", False)
        if autoplay and len(queue) > queue_size:
            # queue_size is 1 greater than previous last index
            new_song_iter = queue.iter_nth_child(None, queue_size)
            app.window.playlist._player.go_to(new_song_iter, True, queue)
            app.window.playlist._player.play()
