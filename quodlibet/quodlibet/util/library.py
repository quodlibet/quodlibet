# -*- coding: utf-8 -*-
# Copyright 2004-2010 Joe Wreschnig, Michael Urman, Iñigo Serna,
#     Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet import config

from quodlibet.parse import Query
from quodlibet.qltk.songlist import SongList

def background_filter():
    bg = config.get("browsers", "background").decode('utf-8')
    if not bg: return
    try: return Query(bg, SongList.star).search
    except Query.error: pass
