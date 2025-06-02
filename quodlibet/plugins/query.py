# Copyright 2016 Ryan Dellenbaugh
#           2020 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from typing import Any

from gi.repository import Gtk

from quodlibet import _
from quodlibet import util
from quodlibet.formats import AudioFile
from quodlibet.plugins import PluginHandler, PluginManager
from quodlibet.qltk import Icons, Align, Frame


def markup_for_syntax(text: str) -> str:
    return f"<b><tt>{util.escape(text)}</tt></b>"


class QueryPlugin:
    """
    Query plugins provide extensions to the search query syntax used in '@'
    queries, like '@(name: body)'

    The plugin must provide the search instance method:

        self.search(song, body)

    The plugin may optionally provide the parse_body method:

        self.parse_body(body)

    This method will be called once, when the query is parsed, with the body
    string from the query, or None if the query contained no body. It should
    return a value representing the parsed body, to be used in self.search.

    If the provided body is invalid, the method may raise a QueryPluginError
    to indicate that all matches should fail. In this case search will not be
    called.
    """

    def search(self, song: AudioFile, body: Any | None) -> bool:
        """Whether to match the given song
        :param song: the song in question
        :param body: the query body
        :returns:  whether the song matches the query for the given body.
        """
        raise NotImplementedError

    key: str | None = None
    """The name used for query syntax, if not the name of the plugin"""

    PLUGIN_ICON = Icons.EDIT_FIND

    usage: str | None = None
    """Override this markup to show example usage for users"""

    def parse_body(self, body: str) -> str:
        return body

    @classmethod
    def PluginPreferences(cls, window):  # noqa
        if not cls.usage:
            return Gtk.Box(orientation=Gtk.Orientation.VERTICAL, )
        label = Gtk.Label(
            label=cls.usage,
            use_markup=True,
            xalign=0.0,
            yalign=0.5,
            wrap=True,
            width_chars=30,
            selectable=True,
        )
        return Frame(
            _("Usage"),
            child=Align(
                label, border=9, halign=Gtk.Align.START, valign=Gtk.Align.START
            ),
        )


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
