# -*- coding: utf-8 -*-
# Copyright 2004-2011 Joe Wreschnig, Michael Urman, Steven Robertson,
#           2011-2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet import config
from quodlibet.player import PlayerError
from quodlibet.player._base import Backend
from quodlibet.player.xinebe.player import XinePlaylistPlayer

from ConfigParser import NoOptionError


class XineBackend(Backend):

    def __init__(self, driver, librarian):
        Backend.__init__(self, driver, librarian)

        self._driver = driver
        self._librarian = librarian

        self._player = None

    def get_player(self):
        if self._player:
            return self._player

        """May raise PlayerError"""

        self._player = XinePlaylistPlayer(self.driver, self._librarian)
        return self._player

    def get_preview_player(self):
        return None


def init(librarian):
    try:
        driver = config.get("settings", "xine_driver")
    except NoOptionError:
        raise PlayerError("Can't find xine driver name: ")
    return XineBackend(driver, librarian)
