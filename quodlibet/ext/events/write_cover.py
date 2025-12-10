# Copyright 2005 Joe Wreschnig
#        2018-25 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


import shutil
from pathlib import Path

from gi.repository import Gtk

import quodlibet
from quodlibet import _, print_w
from quodlibet import app
from quodlibet import config
from quodlibet.plugins.events import EventPlugin
from quodlibet.qltk import Icons


def get_path() -> Path:
    p = config.get("plugins", __name__, default="")
    return Path(p) if p else Path(quodlibet.get_user_dir()) / "current.cover"


def set_path(value):
    config.set("plugins", __name__, str(value))


class PictureSaver(EventPlugin):
    PLUGIN_ID = "Picture Saver"
    PLUGIN_NAME = _("Picture Saver")
    PLUGIN_DESC = _("Saves the cover image of the current song to a file.")
    PLUGIN_ICON = Icons.DOCUMENT_SAVE

    def plugin_on_song_started(self, song):
        def delete(p: Path):
            p.unlink(missing_ok=True)

        path = get_path()
        if song is None:
            delete(path)
        else:
            cover = app.cover_manager.get_cover(song)
            if cover is None:
                delete(path)
            else:
                path.write_bytes(cover.read())

    def PluginPreferences(self, parent):
        def changed(entry):
            fn = entry.get_text()
            try:
                shutil.move(get_path(), fn)
            except OSError as e:
                print_w(f"Couldn't save to new path {fn} ({e})")
            else:
                set_path(fn)

        hb = Gtk.HBox(spacing=6)
        hb.set_border_width(6)
        hb.pack_start(Gtk.Label(label=_("File:")), False, True, 0)
        e = Gtk.Entry()
        e.set_text(str(get_path()))
        e.connect("changed", changed)
        hb.pack_start(e, True, True, 0)
        return hb
