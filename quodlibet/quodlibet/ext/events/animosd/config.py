# -*- coding: utf-8 -*-
# Copyright (C) 2012-13 Nick Boultbee, Thomas Vogt
# Copyright (C) 2008 Andreas Bombe
# Copyright (C) 2005  Michael Urman
# Based on osd.py (C) 2005 Ton van den Heuvel, Joe Wreshnig
#                 (C) 2004 Gustavo J. A. M. Carneiro
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet.plugins import (PluginConfig, ConfProp, IntConfProp,
    FloatConfProp, ColorConfProp)


DEFAULT_PATTERN = (r"<album|[b]<album>[/b]<discnumber| - Disc "
    """<discnumber>><part| - [b]<part>[/b]><tracknumber| - <tracknumber>>
    >[span weight='bold' size='large']<title>[/span] - <~length><version|
    [small][i]<version>[/i][/small]><~people|
    by <~people>>""")


def get_config(prefix):
    class AnimOsdConfig(object):

        plugin_conf = PluginConfig(prefix)

        font = ConfProp(plugin_conf, "font", "Sans 22")
        string = ConfProp(plugin_conf, "string", DEFAULT_PATTERN)
        pos_x = FloatConfProp(plugin_conf, "pos_x", 0.5)
        pos_y = FloatConfProp(plugin_conf, "pos_y", 0.0)
        corners = IntConfProp(plugin_conf, "corners", 1)
        delay = IntConfProp(plugin_conf, "delay", 2500)
        monitor = IntConfProp(plugin_conf, "monitor", 0)
        align = IntConfProp(plugin_conf, "align", 1)
        coversize = IntConfProp(plugin_conf, "coversize", 120)
        text = ColorConfProp(plugin_conf, "text", (0.9, 0.9, 0.9, 0.0))
        outline = ColorConfProp(plugin_conf, "outline", (-1.0, 0.0, 0.0, 0.2))
        shadow = ColorConfProp(plugin_conf, "shadow", (-1.0, 0.0, 0.0, 0.1))
        fill = ColorConfProp(plugin_conf, "fill", (0.25, 0.25, 0.25, 0.5))

    return AnimOsdConfig()
