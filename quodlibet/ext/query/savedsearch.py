# Copyright 2016 Ryan Dellenbaugh
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os.path

from quodlibet import _
from quodlibet.plugins.query import QueryPlugin, QueryPluginError
from quodlibet.query import Query
from quodlibet.query._match import Error as QueryError
from quodlibet import get_user_dir


class IncludeSavedSearchQuery(QueryPlugin):
    PLUGIN_ID = "include_saved"
    PLUGIN_NAME = _("Include Saved Search")
    PLUGIN_DESC = _("Include the results of a saved search as part of another "
                  "query. Syntax is '@(saved: search name)'.")
    key = 'saved'

    def search(self, data, body):
        return body.search(data)

    def parse_body(self, body, query_path_=None):
        if body is None:
            raise QueryPluginError
        body = body.strip().lower()
        # Use provided query file for testing
        if query_path_:
            query_path = query_path_
        else:
            query_path = os.path.join(get_user_dir(), 'lists', 'queries.saved')
        try:
            with open(query_path, 'r', encoding="utf-8") as query_file:
                for query_string in query_file:
                    name = next(query_file).strip().lower()
                    if name == body:
                        try:
                            return Query(query_string.strip())
                        except QueryError:
                            raise QueryPluginError
            # We've searched the whole file and haven't found a match
            raise QueryPluginError
        except IOError:
            raise QueryPluginError
        except StopIteration:
            # The file has an odd number of lines. This shouldn't happen unless
            # it has been externally modified
            raise QueryPluginError
