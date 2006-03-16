# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import config
import gobject
import player
import random
import widgets

class RandomAlbum(object):
    PLUGIN_NAME = 'Random Album Playback'
    PLUGIN_DESC = ("When your playlist reaches its end a new album will "
                   "be chosen randomly and started. It requires that your "
                   "active browser supports filtering by album.")
    PLUGIN_VERSION = '0.15'

    def plugin_on_song_started(self, song):
        if (song is None and config.get("memory", "order") != "onesong"):
            browser = widgets.main.browser
            if browser.can_filter('album'):
                try:
                    values = browser.list("album")
                    if values: album = random.choice(values)
                    else: album = None
                except AttributeError:
                    from library import library
                    album = library.random("album")
                if album is not None:
                    browser.filter('album', [album])
                    gobject.idle_add(self.unpause)

    def unpause(self):
        # Wait for the next GTK loop to make sure everything's tidied up
        # after the song ended. Also, if this is program startup and the
        # previous current song wasn't found, we'll get this condition
        # as well, so just leave the player paused if that's the case.
        try: player.playlist.next()
        except AttributeError: player.playlist.paused = True
