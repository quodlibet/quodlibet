# -*- coding: utf-8 -*-
# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet import app
from quodlibet.qltk.notif import Task
from quodlibet.qltk import Icons
from quodlibet.util import copool

from quodlibet.plugins.songsmenu import SongsMenuPlugin


class RefreshSongs(SongsMenuPlugin):
    PLUGIN_ID = "refresh-songs"
    # Translators: Plugin name
    PLUGIN_NAME = _("Rescan Songs")
    PLUGIN_DESC = _("Checks for file changes and reloads / removes "
                    "the songs if needed.")
    PLUGIN_ICON = Icons.VIEW_REFRESH

    def plugin_songs(self, songs):

        def check_songs():
            desc = ngettext("%d song", "%d songs", len(songs)) % len(songs)
            with Task(_("Rescan songs"), desc) as task:
                task.copool(check_songs)
                for i, song in enumerate(songs):
                    song = song._song
                    if song in app.library:
                        app.library.reload(song)
                    task.update((float(i) + 1) / len(songs))
                    yield

        copool.add(check_songs)
