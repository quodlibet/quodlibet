# Copyright 2016 Ryan Dellenbaugh
#           2020 Nick Boultbee
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import _
from quodlibet.plugins.query import QueryPlugin, QueryPluginError, markup_for_syntax
from quodlibet.query._parser import QueryParser


class ConditionalQuery(QueryPlugin):
    PLUGIN_ID = "conditional_query"
    PLUGIN_NAME = _("Conditional Query")
    PLUGIN_DESC = _("Chooses the query to match based on a condition query.")
    key = 'if'
    query_syntax = _("@(if: condition-query, then-query, else-query)")
    usage = markup_for_syntax(query_syntax)

    def search(self, song, body):
        if body[0].search(song):
            return body[1].search(song)
        else:
            return body[2].search(song)

    def parse_body(self, body):
        if body is None:
            raise QueryPluginError
        parser = QueryParser(body)
        queries = parser.match_list(parser.Query)
        if len(queries) != 3:
            raise QueryPluginError
        return queries
