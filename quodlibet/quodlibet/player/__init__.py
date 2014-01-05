# Copyright 2007 Joe Wreschnig
#           2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet import const
from quodlibet import util


class PlayerError(Exception):
    def __init__(self, short_desc, long_desc):
        self.short_desc = short_desc
        self.long_desc = long_desc


def init(backend_name):
    """Imports the player backend module for the given name.
    Raises PlayerError if the import fails.

    the module provides the following functions:
        init(librarian) -> new player instance
    """

    modulename = "quodlibet.player." + backend_name

    try:
        backend = __import__(modulename, {}, {}, "quodlibet.player")
    except ImportError:
        if const.DEBUG:
            util.print_exc()

        raise PlayerError(
            _("Invalid audio backend"),
            _("The audio backend %r is not installed.") % backend_name)
    else:
        return backend
