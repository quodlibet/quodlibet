from tests import TestCase, add

from player import PlaylistPlayer
from qltk.controls import PlayControls, Volume
from library import SongLibrary

class TPlayControls(TestCase):
    def test_ctr(self):
        PlayControls(PlaylistPlayer('fakesink'), SongLibrary()).destroy()
add(TPlayControls)
