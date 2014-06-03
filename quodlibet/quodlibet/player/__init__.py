# Copyright 2007 Joe Wreschnig
#           2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet import const
from quodlibet import util


class PlayerError(Exception):
    """Error raised by player loading/initialization and emitted by the
    error signal during playback.

    Both short_desc and long_desc are meant for displaying in the UI.
    They should be unicode.
    """

    def __init__(self, short_desc, long_desc=None):
        self.short_desc = short_desc
        self.long_desc = long_desc

    def __unicode__(self):
        return self.short_desc + (
            u"\n" + self.long_desc if self.long_desc else u"")

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __repr__(self):
        return "%s(%r, %r)" % (
            type(self).__name__, repr(self.short_desc), repr(self.long_desc))


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
            _("The audio backend '%(backend-name)s' could not be loaded.") % {
                "backend-name": backend_name})
    else:
        return backend
