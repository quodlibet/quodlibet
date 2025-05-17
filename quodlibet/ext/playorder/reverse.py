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
    PLUGIN_DESC = _("Adds a shuffle mode that reverses the play order of songs.")
    display_name = _("Reverse")
    accelerated_name = _("Re_verse")

    def previous(self, playlist, iter):
        return super().next(playlist, iter)

    def next(self, playlist, iter):
        return super().previous(playlist, iter)
