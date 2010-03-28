# -*- coding: utf-8 -*-
# Copyright 2010 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

from quodlibet.plugins.playorder import PlayOrderPlugin, \
    PlayOrderRememberedMixin, PlayOrderInOrderMixin

# Importing main directly fails, as it is assigned after this file is read
from quodlibet import widgets

class FollowOrder(PlayOrderPlugin, PlayOrderRememberedMixin,
    PlayOrderInOrderMixin):
    PLUGIN_ID = "follow"
    PLUGIN_NAME = _("Follow Cursor")
    PLUGIN_ICON = "gtk-jump-to"
    PLUGIN_VERSION = "1"
    PLUGIN_DESC = ("Playback follows your selection.")

    __last_path = None

    def next(self, playlist, iter):
        next_fallback = PlayOrderInOrderMixin.next(self, playlist, iter)
        PlayOrderRememberedMixin.next(self, playlist, iter)

        selected = widgets.main.songlist.get_selected_songs()
        if not selected:
            return next_fallback

        selected_iter = playlist.find(selected[0])
        selected_path = playlist.get_path(selected_iter)
        current_path = iter and playlist.get_path(iter)

        if selected_path in (current_path, self.__last_path):
            return next_fallback

        self.__last_path = selected_path
        return selected_iter

    def set(self, playlist, iter):
        if iter:
            self.__last_path = playlist.get_path(iter)
        return super(FollowOrder, self).set(playlist, iter)

    def reset(self, playlist):
        super(FollowOrder, self).reset(playlist)
        self.__last_path = None
