# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

PLUGIN_NAME = 'Random Album Playback'
PLUGIN_DESC = ("When your playlist reaches its end a new album will "
               "be chosen randomly and started. It requires that your "
               "active browser support filtering by album.")
PLUGIN_VERSION = '0.13'

import gobject
import library, player
from widgets import widgets

def plugin_on_song_started(song):
    if song is None:
        browser = widgets.main.browser
        album = library.library.random("album")
        if browser.can_filter('album') and album:
            browser.filter('album', [album])
            gobject.idle_add(unpause)

def unpause():
    # Wait for the next GTK loop to make sure everything's tidied up
    # after the song ended. Also, if this is program startup and the
    # previous current song wasn't found, we'll get this condition
    # as well, so just leave the player paused if that's the case.
    try: player.playlist.next()
    except AttributeError: player.playlist.paused = True
        
    
