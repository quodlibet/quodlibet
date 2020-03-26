# Copyright 2016 Ryan Dellenbaugh
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet.plugins import PluginHandler, PluginManager
from quodlibet.qltk import Icons


class QueryPlugin(object):
    """
    Query plugins provide extensions to the search query syntax used in '@'
    queries, like '@(name: body)'

    The plugin must provide the search instance method:

        self.search(song, body)

    This method is passed a song and the query body and should return a boolean
    value indicating whether the song matches the query for the given query
    body.

    The song argument will be an instance of quodlibet.formats.Audiofile,
    implementing a dict interface for retrieving tags.

    The body argument will be the query body as a string, or None if the query
    contained no body. If the self.parse_body method is implemented, it will
    instead be the value returned from that.

    The plugin may optionally provide the parse_body method:

        self.parse_body(body)

    This method will be called once, when the query is parsed, with the body
    string from the query, or None if the query contained no body. It should
    return a value representing the parsed body, to be used in self.search.

    If the provided body is invalid, the method may raise a QueryPluginError
    to indicate that all matches should fail. In this case search will not be
    called.

    By default, the name used in the '@(name)' query to use the plugin is
    the PLUGIN_NAME attribute. However, this can be changed by overriding
    the 'key' attribute to a different string to be used.
    """
    search = None
    key = None
    PLUGIN_ICON = Icons.EDIT_FIND

    def parse_body(self, body):
        return body


class QueryPluginError(Exception):
    pass


class QueryPluginHandler(PluginHandler):
    """Maintains a dictionary of enabled Query Plugins by key"""

    def init_plugins(self):
        PluginManager.instance.register_handler(self)

    def __init__(self):
        self.plugins = {}

    def plugin_handle(self, plugin):
        return issubclass(plugin.cls, QueryPlugin)

    def plugin_enable(self, plugin):
        self.plugins[plugin.cls.key or plugin.name] = plugin.cls()

    def plugin_disable(self, plugin):
        del self.plugins[plugin.cls.key or plugin.name]

    def get_plugin(self, key):
        return self.plugins[key]

QUERY_HANDLER = QueryPluginHandler()
