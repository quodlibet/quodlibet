# -*- coding: utf-8 -*-
# Copyright 2004-2011 Joe Wreschnig, Michael Urman, Steven Robertson,
#           2011-2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gi
try:
    gi.require_version("Gst", "1.0")
    gi.require_version("GstPbutils", "1.0")
except ValueError as e:
    raise ImportError(e)

from gi.repository import Gst

from quodlibet import const

from quodlibet.player._base import Backend
from quodlibet.player.gstbe.player import GStreamerPlayer

from .plugins import GStreamerPluginHandler
from .prefs import GstBackendPreferences


class GStreamerBackend(Backend, GStreamerPluginHandler):

    def BackendPreferences(self):
        return GstBackendPreferences(self, const.DEBUG)

    def __init__(self, librarian):
        GStreamerPluginHandler.__init__(self)
        Backend.__init__(self, librarian)

        self._librarian = librarian

        self._player = None
        self._preview_player = None

        # Enable error messages by default
        if Gst.debug_get_default_threshold() == Gst.DebugLevel.NONE:
            Gst.debug_set_default_threshold(Gst.DebugLevel.ERROR)

    def get_player(self):
        if self._player:
            return self._player

        self._player = GStreamerPlayer(self._librarian)
        return self._player

    def get_preview_player(self):
        if self._preview_player:
            return self._preview_player

        self._preview_player = GStreamerPlayer(self._librarian, True)
        return self._preview_player


def init(librarian):
    return GStreamerBackend(librarian)
