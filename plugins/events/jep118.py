# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import util

from plugins.events import EventPlugin

outfile = os.path.expanduser("~/.quodlibet/jabber")
format = """\
<tune xmlns='http://jabber.org/protocol/tune'>
 <artist>%s</artist>
 <title>%s</title>
 <source>%s</source>
 <track>%d</track>
 <length>%d</length>
</tune>"""

class JEP118(EventPlugin):
    PLUGIN_ID = "JEP-118"
    PLUGIN_NAME = "JEP-118"
    PLUGIN_DESC = "Output a Jabber User Tunes file to ~/.quodlibet/jabber"
    PLUGIN_ICON = 'gtk-save'
    PLUGIN_VERSION = "0.13"

    def plugin_on_song_started(self, song):
        if song is None:
            try:
                f = file(outfile, "w")
                f.write("<tune xmlns='http://jabber.org/protocol/tune'/>")
            except EnvironmentError: pass
            else: f.close()
        else:
            try:
                f = file(outfile, "wb")
                f.write(format % (
                    util.escape(song.comma("artist")),
                    util.escape(song.comma("title")),
                    util.escape(song.comma("album")),
                    song("~#track", 0), song.get("~#length", 0)))
            except EnvironmentError: pass
            else: f.close()
