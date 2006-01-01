# -*- coding: utf-8 -*-
# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import const
from plugins._manager import Manager

class RenameFilesPlugin(object):
    """Plugins of this type must subclass a GTK widget. They will be
    packed into the RenameFiles pane (currently a ScrolledWindow hidden
    with an expander, but that might change).

    The 'filter' function will be called with the proposed filename
    as a unicode object. It should return an appropriate-transformed
    filename, still as a unicode object.

    The plugin must provide either a 'changed' or 'preview'. 'changed'
    causes the entire display to be re-previewed (e.g. via a checkbox).
    'preview' causes the Preview button to made sensitive, and Save
    to be disabled.

    If the 'active' attribute is false, the filter will not be called.
    This is particularly useful for gtk.CheckButtons."""

    active = False
    def filter(self, value): return value

class EditingPlugins(Manager):
    __PATHS = [os.path.join("./plugins", "editing"),
               os.path.join(const.PLUGINS, "editing")]

    def __init__(self):
        super(EditingPlugins, self).__init__(self.__PATHS)

    def RenamePlugins(self):
        return super(EditingPlugins, self).find_subclasses(RenameFilesPlugin)
