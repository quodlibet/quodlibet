# -*- coding: utf-8 -*-
# Copyright 2009 Steven Robertson
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

from quodlibet.plugins.playorder import PlayOrderPlugin, PlayOrderInOrderMixin

# Importing main directly fails, as it is assigned after this file is read
from quodlibet import widgets

class QueueOrder(PlayOrderPlugin, PlayOrderInOrderMixin):
    PLUGIN_ID = "queue"
    PLUGIN_NAME = _("Queue Only")
    PLUGIN_ICON = "gtk-media-next"
    PLUGIN_VERSION = "1"
    PLUGIN_DESC = ("Only songs in the queue will be played. Double-click on "
                   "any song to enqueue it.")

    def next(self, playlist, iter):
        return None

    def set_explicit(self, playlist, iter):
        if iter is None: return
        song = playlist[iter][0]
        if song is None: return
        widgets.main.playlist.enqueue([playlist[iter][0]])

