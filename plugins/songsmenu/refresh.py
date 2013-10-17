# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet import app
from quodlibet.qltk.notif import Task
from quodlibet.util import copool

from quodlibet.plugins.songsmenu import SongsMenuPlugin


class RefreshSongs(SongsMenuPlugin):
    PLUGIN_ID = "refresh-songs"
    PLUGIN_NAME = _("Refresh Songs")
    PLUGIN_DESC = _("Checks for file changes and reloads/removes"
                    "the songs if needed")
    PLUGIN_ICON = 'gtk-refresh'

    def plugin_songs(self, songs):

        def check_songs():
            with Task(_("Refresh songs"), _("%d songs") % len(songs)) as task:
                task.copool(check_songs)
                for i, song in enumerate(songs):
                    song = song._song
                    if song in app.library:
                        app.library.reload(song)
                    task.update((float(i) + 1) / len(songs))
                    yield

        copool.add(check_songs)
