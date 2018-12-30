# Copyright 2017 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


from quodlibet.library import SongLibrarian
from quodlibet.player import PlayerError

try:
    from quodlibet.player.xinebe.player import XinePlaylistPlayer
except ImportError:
    XinePlaylistPlayer = None

from . import TestCase, skipUnless


@skipUnless(XinePlaylistPlayer is not None, "no xinebe")
class TXinePlaylistPlayer(TestCase):

    def test_init(self):
        try:
            player = XinePlaylistPlayer(None, SongLibrarian())
        except PlayerError:
            # travis has no output
            pass
        else:
            player.destroy()

    def test_init_device_non_existing(self):
        with self.assertRaises(PlayerError):
            XinePlaylistPlayer(b"this is not a device", SongLibrarian())
