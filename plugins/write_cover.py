# Copyright 2004-2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, util

OUTFILE = os.path.expanduser("~/.quodlibet/current.cover")

PLUGIN_NAME = "Picture Saver"
PLUGIN_DESC = "The cover image of the current song is saved to %s" % util.unexpand(OUTFILE)

def plugin_on_song_started(song):
    if song is None:
        try: os.unlink(OUTFILE)
        except EnvironmentError: pass
    else:
        cover = song.find_cover()
        if cover is None:
            try: os.unlink(OUTFILE)
            except EnvironmentError: pass
        else:
            f = file(OUTFILE, "wb")
            f.write(cover.read())
            f.close()
