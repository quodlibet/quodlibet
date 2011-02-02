# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import shutil

import gtk

from quodlibet import config
from quodlibet.plugins.events import EventPlugin

try: config.get("plugins", __name__)
except:
    out = os.path.expanduser("~/.quodlibet/current.cover")
    config.set("plugins", __name__, out)

class PictureSaver(EventPlugin):
    PLUGIN_ID = "Picture Saver"
    PLUGIN_NAME = _("Picture Saver")
    PLUGIN_DESC = "The cover image of the current song is saved to a file."
    PLUGIN_ICON = gtk.STOCK_SAVE
    PLUGIN_VERSION = "0.21"

    def plugin_on_song_started(self, song):
        outfile = config.get("plugins", __name__)
        if song is None:
            try: os.unlink(outfile)
            except EnvironmentError: pass
        else:
            cover = song.find_cover()
            if cover is None:
                try: os.unlink(outfile)
                except EnvironmentError: pass
            else:
                f = file(outfile, "wb")
                f.write(cover.read())
                f.close()

    def PluginPreferences(self, parent):
        def changed(entry):
            fn = entry.get_text()
            try: shutil.move(config.get("plugins", __name__), fn)
            except EnvironmentError: pass
            else: config.set("plugins", __name__, fn)

        hb = gtk.HBox(spacing=6)
        hb.set_border_width(6)
        hb.pack_start(gtk.Label(_("File:")), expand=False)
        e = gtk.Entry()
        e.set_text(config.get("plugins", __name__))
        e.connect('changed', changed)
        hb.pack_start(e)
        return hb
