# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import _
from quodlibet.plugins.playorder import ShufflePlugin
from quodlibet.qltk import Icons
from quodlibet.qltk.playorder import OrderInOrder


class ReverseOrder(ShufflePlugin, OrderInOrder):
    PLUGIN_ID = "reverse"
    PLUGIN_NAME = _("Reverse")
    PLUGIN_ICON = Icons.MEDIA_SKIP_BACKWARD
    PLUGIN_DESC = _("Reverses the play order of songs.")

    def previous(self, playlist, iter):
        return super(ReverseOrder, self).next(playlist, iter)

    def next(self, playlist, iter):
        return super(ReverseOrder, self).previous(playlist, iter)
