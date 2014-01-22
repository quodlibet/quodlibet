from tests import TestCase

from quodlibet import config
from quodlibet.qltk.maskedbox import MaskedBox
from quodlibet.library import SongFileLibrary


class TMaskedBox(TestCase):
    def setUp(self):
        config.init()

    def tearDown(self):
        config.quit()

    def test(self):
        lib = SongFileLibrary()
        MaskedBox(lib).destroy()
