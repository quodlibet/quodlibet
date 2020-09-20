# Copyright 2010 Christoph Reiter
#           2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet.plugins.playorder import ShufflePlugin
from quodlibet.order import OrderInOrder, OrderRemembered
from quodlibet import _
from quodlibet import app
from quodlibet.qltk import Icons


class FollowOrder(ShufflePlugin, OrderInOrder, OrderRemembered):
    PLUGIN_ID = "follow"
    PLUGIN_NAME = _("Follow Cursor")
    PLUGIN_ICON = Icons.GO_JUMP
    PLUGIN_DESC = _("Playback follows your selection, "
                    "or the next song in the list once exhausted.")

    __last_path = None

    def next(self, playlist, iter):
        next_fallback = OrderInOrder.next(self, playlist, iter)
        OrderRemembered.next(self, playlist, iter)

        selected = app.window.songlist.get_selected_songs()
        if not selected:
            return next_fallback

        selected_iter = playlist.find(selected[0])
        selected_path = playlist.get_path(selected_iter)
        current_path = iter and playlist.get_path(iter)

        if selected_path in (current_path, self.__last_path):
            return next_fallback

        self.__last_path = selected_path
        return selected_iter

    def previous(self, *args):
        self.__last_path = None
        return super().previous(*args)

    def set(self, playlist, iter):
        if iter:
            self.__last_path = playlist.get_path(iter)
        return super().set(playlist, iter)

    def reset(self, playlist):
        super().reset(playlist)
        self.__last_path = None
