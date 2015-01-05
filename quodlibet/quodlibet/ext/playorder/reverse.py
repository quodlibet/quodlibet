# -*- coding: utf-8 -*-
from quodlibet.plugins.playorder import PlayOrderPlugin, PlayOrderInOrderMixin


class ReverseOrder(PlayOrderPlugin, PlayOrderInOrderMixin):
    PLUGIN_ID = "reverse"
    PLUGIN_NAME = _("Reverse")
    PLUGIN_ICON = "gtk-refresh"
    PLUGIN_DESC = _("Reverses the play order of songs.")

    def previous(self, playlist, iter):
        return super(ReverseOrder, self).next(playlist, iter)

    def next(self, playlist, iter):
        return super(ReverseOrder, self).previous(playlist, iter)
