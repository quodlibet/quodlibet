# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import _
from quodlibet.plugins.events import EventPlugin
from quodlibet.qltk import Icons


class AutoRating(EventPlugin):
    PLUGIN_ID = "Automatic Rating"
    PLUGIN_NAME = _("Automatic Rating")
    PLUGIN_DESC = _("Rates songs automatically when they are played or "
                    "skipped. This uses the 'accelerated' algorithm from "
                    "vux (Vacillating Utilitarian eXtemporizer) "
                    "by Brian Nelson.")
    PLUGIN_ICON = Icons.USER_BOOKMARKS

    def plugin_on_song_ended(self, song, skipped):
        if song is not None:
            rating = song("~#rating")
            invrating = 1.0 - rating
            delta = min(rating, invrating) / 2.0
            if skipped:
                rating -= delta
            else:
                rating += delta
            song["~#rating"] = rating
