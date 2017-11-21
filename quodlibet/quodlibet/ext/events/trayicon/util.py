# -*- coding: utf-8 -*-
# Copyright 2004-2006 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2012 Christoph Reiter
#           2013 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import config
from quodlibet.plugins import PluginConfig


DEFAULT_PATTERN = ("<album|<album~discnumber~part~tracknumber~title~version>|"
                   "<artist~title~version>>")


def _get_plugin_config():
    # migrate option
    if config.has_option('plugins', 'trayicon_window_hide'):
        value = config.getboolean('plugins', 'trayicon_window_hide')
        config.remove_option('plugins', 'trayicon_window_hide')
        config.set('plugins', 'icon_window_hide', value)

    pconfig = PluginConfig("icon")
    pconfig.defaults.set("window_hide", True)
    pconfig.defaults.set("tooltip", DEFAULT_PATTERN)
    pconfig.defaults.set("modifier_swap", False)

    return pconfig


pconfig = _get_plugin_config()
