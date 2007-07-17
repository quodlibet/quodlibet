import os

from imagen.png import PNG
from tests import TestCase, add

class TPNG(TestCase):

    def setUp(self):
        self.image = PNG(os.path.join(
            "tests", "data", "black817-480x360-3.5.png"))

    def test_chunk_count(self):
        self.failUnlessEqual(len(self.image.chunks), 5)

    def test_chunk_first(self):
        self.failUnlessEqual(self.image.chunks[0].type, "IHDR")

    def test_chunk_last(self):
        self.failUnlessEqual(self.image.chunks[-1].type, "IEND")

    def test_repr(self):
        repr(self.image)

add(TPNG)

class TBadPNG(TestCase):

    def test_garbage_file(self):
        self.failUnlessRaises(
            IOError, PNG, os.path.join("tests", "data", "garbage.png"))

add(TBadPNG)
