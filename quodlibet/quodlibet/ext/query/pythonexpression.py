# -*- coding: utf-8 -*-
# Copyright 2016 Ryan Dellenbaugh
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet import _
from quodlibet.plugins.query import QueryPlugin, QueryPluginError


class PythonQuery(QueryPlugin):
    PLUGIN_ID = "python_query"
    PLUGIN_NAME = _("Python Query")
    PLUGIN_DESC = _("Use Python expressions in queries. Syntax is '@(python: "
                  "expression)'. The variable 's' is the song being matched.")
    key = 'python'

    def search(self, data, body):
        try:
            return eval(body, {'s': data})
        except:
            return False

    def parse_body(self, body):
        if body is None:
            raise QueryPluginError
        try:
            return compile(body.strip(), 'query', 'eval')
        except SyntaxError:
            raise QueryPluginError
