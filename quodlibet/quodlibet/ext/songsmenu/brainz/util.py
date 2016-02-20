# -*- coding: utf-8 -*-
# Copyright 2005-2010   Joshua Kwan <joshk@triplehelix.org>,
#                       Michael Ball <michael.ball@gmail.com>,
#                       Steven Robertson <steven@strobe.cc>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet.plugins import PluginConfig


def get_config():
    pc = PluginConfig("brainz")

    defaults = pc.defaults
    defaults.set("year_only", False)
    defaults.set("albumartist", True)
    defaults.set("artist_sort", False)
    defaults.set("standard", True)

    return pc


pconfig = get_config()
