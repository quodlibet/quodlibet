from tests import TestCase, add, DATA_DIR

import os

from quodlibet.formats.mod import ModFile, extensions

class TModFile(TestCase):
    def setUp(self):
        self.song = ModFile(os.path.join(DATA_DIR, 'empty.xm'))

    def test_length(self):
        self.failUnlessEqual(0, self.song("~#length", 0))

    def test_title(self):
        self.failUnlessEqual("test song", self.song["title"])

if extensions:
    add(TModFile)
else:
    print "WARNING: Skipping ModFile tests. Install ModPlug."
