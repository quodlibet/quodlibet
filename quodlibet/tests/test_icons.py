# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk

from tests import TestCase, add
from quodlibet import const

class TIconTheme(TestCase):
    def test_icon_theme(self):
        theme = gtk.icon_theme_get_default()
        theme.append_search_path(const.IMAGEDIR)

        for i in ["audio-volume-high", "audio-volume-high",
            "audio-volume-medium", "audio-volume-muted",
            "multimedia-player", "multimedia-player-apple-ipod",
            "quodlibet", "exfalso", "quodlibet-missing-cover",
            "media-eject", "multimedia-player-ipod", "user-trash"]:
            self.failUnless(theme.has_icon(i))

add(TIconTheme)
