# -*- coding: utf-8 -*-
# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import const
from plugins._manager import Manager

class FIFOPlugin(object):
    """A FIFO plugin constructor is called if the FIFO command given
    is in the 'commands' attribute, which is a list of strings.
    It is called with the command, value (if any), watcher, main window,
    and player.

    The '_order' attribute can be changed to give one plugin a higher
    priority than another. Only one plugin will be called per command."""

    commands = []
    _order = 0

class RemotePlugins(Manager):
    __PATHS = [os.path.join("./plugins", "remote"),
               os.path.join(const.PLUGINS, "remote")]

    def __init__(self):
        super(RemotePlugins, self).__init__(self.__PATHS)

    def FIFOPlugins(self):
        plugins = super(RemotePlugins, self).find_subclasses(FIFOPlugin)
        plugins.sort(
            lambda A, B: cmp(A._order, B._order) or cmp(A.__name__, B.__name__))
        return plugins

