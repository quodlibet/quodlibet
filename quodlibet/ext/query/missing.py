# Copyright 2018 Peter Strulo
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk
from quodlibet import _
from quodlibet.plugins.query import QueryPlugin
from quodlibet.plugins import PluginConfigMixin
from quodlibet.qltk import Frame


class MissingQuery(QueryPlugin, PluginConfigMixin):
    PLUGIN_ID = "missing_query"
    PLUGIN_NAME = _("Missing Query")
    PLUGIN_DESC = _("Matches songs without the given tag.")
    key = 'missing'
    usage = "<b><tt>@(missing: artist)</tt></b>"

    def search(self, data, body):
        val = data.get(body.strip() if body else '', None)
        return (val is None
                or (self.config_get_bool("include_empty", True)
                    and val == ""))

    @classmethod
    def PluginPreferences(cls, window):
        example = super().PluginPreferences(window)
        box = Gtk.VBox()
        box.pack_start(example, True, True, 0)

        prefs_box = Gtk.VBox()
        button = cls.ConfigCheckButton(_("Include empty tags"),
                                       "include_empty", True)
        prefs_box.pack_start(button, False, False, 6)
        frame = Frame(_("Preferences"), child=prefs_box)
        box.pack_start(frame, True, True, 12)
        return box
