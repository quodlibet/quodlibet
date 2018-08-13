# -*- coding: utf-8 -*-
# Copyright 2018 Peter Strulo
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import _
from quodlibet.plugins.query import QueryPlugin


class MissingQuery(QueryPlugin):
    PLUGIN_ID = "missing_query"
    PLUGIN_NAME = _("Missing Query")
    PLUGIN_DESC = _("Matches songs without the given tag")
    key = 'missing'

    @staticmethod
    def search(data, body):
        if data.get(body, None) is None:
            return True
        return False
