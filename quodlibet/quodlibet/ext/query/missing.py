# -*- coding: utf-8 -*-
# Copyright 2018 Peter Strulo
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import _
from quodlibet.plugins.query import QueryPlugin
from quodlibet.plugins import PluginConfigMixin


class MissingQuery(QueryPlugin, PluginConfigMixin):
    PLUGIN_ID = "missing_query"
    PLUGIN_NAME = _("Missing Query")
    PLUGIN_DESC = _("Matches songs without the given tag.")
    key = 'missing'

    def search(self, data, body):
        val = data.get(body.strip(), None)
        return (val is None
                or (self.config_get_bool("include_empty", True)
                    and val == ""))

    @classmethod
    def PluginPreferences(cls, window):
        return cls.ConfigCheckButton(_("Include empty tags"),
                                     "include_empty", True)
