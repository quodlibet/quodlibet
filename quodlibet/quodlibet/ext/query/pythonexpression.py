# -*- coding: utf-8 -*-

from quodlibet.plugins.query import QueryPlugin, QueryPluginError

class PythonQuery(QueryPlugin):
    PLUGIN_ID = "python_query"
    PLUGIN_NAME = _("Python Query")
    PLUGIN_DESC = _("Use python expressions in queries. Syntax is '@(python: "
                  "expression)'. The variable 's' is the song being matched.")
    key = 'python'
    
    def search(self, data, body):
        try
            return eval(body, {'s': data})
        except:
            return False
        
    def parse_body(self, body):
        try:
            return compile(body, 'query', 'eval')
        except SyntaxError:
            raise QueryPluginError