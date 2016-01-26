# -*- coding: utf-8 -*-

import os.path

from quodlibet.plugins.query import QueryPlugin, QueryPluginError
from quodlibet.query import Query
from quodlibet.query._match import error as QueryError
from quodlibet import get_user_dir

class IncludeSavedSearchQuery(QueryPlugin):
    PLUGIN_ID = "include_saved"
    PLUGIN_NAME = _("Include Saved Search")
    PLUGIN_DESC = _("Include the results of a saved search as part of another "
                  "query. Syntax is '@(saved: search name)'.")
    key = 'saved'
    
    def search(self, data, body):
        return body.search(data)
        
    def parse_body(self, body):
        body = body.strip().lower()
        query_path = os.path.join(get_user_dir(), 'lists', 'queries.saved')
        try:
            with open(query_file, 'rU') as query_file:
                for query_string in query_file:
                    name = next(query_file).strip().lower()
                    if name == body:
                        try:
                            return Query(query_string)
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