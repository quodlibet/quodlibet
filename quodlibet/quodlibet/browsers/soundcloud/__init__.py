# -*- coding: utf-8 -*-
# Copyright 2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet import app
from .main import SoundcloudBrowser

browsers = ([SoundcloudBrowser]
            if not app.player or app.player.can_play_uri("http://")
            else [])
