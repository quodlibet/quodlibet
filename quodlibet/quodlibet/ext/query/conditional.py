# -*- coding: utf-8 -*-
# Copyright 2016 Ryan Dellenbaugh
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import _
from quodlibet.plugins.query import QueryPlugin, QueryPluginError
from quodlibet.query._parser import QueryParser


class ConditionalQuery(QueryPlugin):
    PLUGIN_ID = "conditional_query"
    PLUGIN_NAME = _("Conditional Query")
    PLUGIN_DESC = _("Chooses the query to match based on a condition query. "
                  "Syntax is '@(if: condition, then, else)'.")
    key = 'if'

    def search(self, data, body):
        if body[0].search(data):
            return body[1].search(data)
        else:
            return body[2].search(data)

    def parse_body(self, body):
        if body is None:
            raise QueryPluginError
        parser = QueryParser(body)
        queries = parser.match_list(parser.Query)
        if len(queries) != 3:
            raise QueryPluginError
        return queries
