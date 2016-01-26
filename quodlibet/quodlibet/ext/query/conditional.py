# -*- coding: utf-8 -*-

from quodlibet.plugins.query import QueryPlugin, QueryPluginError
from quodlibet.query._parser import QueryParser

class ConditionalQuery(QueryPlugin):
    PLUGIN_ID = "conditional_query"
    PLUGIN_NAME = _("Conditional Query")
    PLUGIN_DESC _("Chooses the query to match based on a condition query. "
                  "Syntax is '@(if: condition, then, else)'")
    key = 'if'
    
    def search(self, data, body):
        if body[0].search(data):
            return body[1].search(data)
        else:
            return body[2].search(data)
        
    def parse_body(self, body):
        parser = QueryParser(body)
        queries = parser.match_list(parser.Query)
        if len(queries) != 3:
            raise QueryPluginError
        return queries