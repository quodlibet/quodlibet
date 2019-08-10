# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import shelve

from tests import mkstemp

from quodlibet.plugins.events import EventPlugin


class PickleMe(object):
    pass


class PickleTestPlugin(EventPlugin):
    PLUGIN_ID = "pickle_plugin"
    PLUGIN_NAME = "This is a test"

    def enabled(self):
        # https://github.com/quodlibet/quodlibet/issues/1093
        fd, filename = mkstemp('.shelve')
        os.close(fd)
        os.unlink(filename)
        s = shelve.open(filename)
        s["foobar"] = PickleMe()
        s.close()
