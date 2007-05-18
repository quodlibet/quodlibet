from tests import TestCase, add

from quodlibet.player import PlaylistPlayer
from quodlibet.qltk.controls import PlayControls, Volume
from quodlibet.library import SongLibrary

class TPlayControls(TestCase):
    def test_ctr(self):
        PlayControls(PlaylistPlayer('fakesink'), SongLibrary()).destroy()
add(TPlayControls)
