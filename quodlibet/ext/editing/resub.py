# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import re

from gi.repository import Gtk, GObject

from quodlibet import _
from quodlibet.plugins.editing import RenameFilesPlugin, TagsFromPathPlugin
from quodlibet.util import connect_obj
from quodlibet.qltk import Icons


class RegExpSub(Gtk.HBox, RenameFilesPlugin, TagsFromPathPlugin):
    PLUGIN_ID = "Regex Substitution"
    PLUGIN_NAME = _("Regex Substitution")
    PLUGIN_DESC_MARKUP = _(
        "Allows arbitrary regex substitutions (<tt>s/from/to/</tt>) "
        "when tagging or renaming files.")
    PLUGIN_ICON = Icons.EDIT_FIND_REPLACE

    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_LAST, None, ())
    }
    active = True

    def __init__(self):
        super().__init__()
        self._from = Gtk.Entry()
        self._to = Gtk.Entry()
        self.pack_start(Gtk.Label("s/"), True, True, 0)
        self.pack_start(self._from, True, True, 0)
        self.pack_start(Gtk.Label("/"), True, True, 0)
        self.pack_start(self._to, True, True, 0)
        self.pack_start(Gtk.Label("/"), True, True, 0)

        connect_obj(self._from, "changed", self.emit, "changed")
        connect_obj(self._to, "changed", self.emit, "changed")

    def filter(self, orig_or_tag, value):
        fr = self._from.get_text()
        to = self._to.get_text()
        try:
            return re.sub(fr, to, value)
        except Exception:
            return value
