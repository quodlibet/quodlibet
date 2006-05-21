from tests import TestCase, add

import os

from formats.mod import ModFile

class TModFile(TestCase):
    def setUp(self):
        self.song = ModFile(os.path.join('tests', 'data', 'empty.xm'))

    def test_length(self):
        self.failUnlessEqual(0, self.song["~#length"])

    def test_title(self):
        self.failUnlessEqual("test song", self.song["title"])
add(TModFile)
