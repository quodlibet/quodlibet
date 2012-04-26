# -*- coding: utf-8 -*-
# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet.plugins._pluginmanager import PluginManager
from quodlibet.plugins._pluginmanager import PluginImportException


def init(folders=None):
    manager = PluginManager.instance = PluginManager(folders)
    return manager

def quit():
    PluginManager.instance.save()
    PluginManager.instance.quit()
    PluginManager.instance = None
