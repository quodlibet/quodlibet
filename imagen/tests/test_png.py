import os

from imagen.png import PNG, Chunks
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

    def test_getitem(self):
        self.image["IHDR"]

    def test_getitem_no_key(self):
        self.failUnlessRaises(KeyError, self.image.__getitem__, "poop")

    def test_repr(self):
        repr(self.image)

add(TPNG)

class TBadPNG(TestCase):

    def test_garbage_file(self):
        self.failUnlessRaises(
            IOError, PNG, os.path.join("tests", "data", "garbage.png"))

add(TBadPNG)

class TtEXt(TestCase):

    def setUp(self):
        self.chunk = Chunks["tEXt"]("key\x00value")

    def test_get_keyword(self):
        self.failUnlessEqual(self.chunk.keyword, "key")

    def test_set_keyword(self):
        self.chunk.keyword = "another key"
        self.failUnlessEqual(self.chunk.keyword, "another key")
        self.failUnlessEqual(self.chunk.string, "value")

    def test_get_string(self):
        self.failUnlessEqual(self.chunk.string, "value")

    def test_set_string(self):
        self.chunk.string = "another value"
        self.failUnlessEqual(self.chunk.keyword, "key")
        self.failUnlessEqual(self.chunk.string, "another value")

    def test_set_invalid_unicode_keyword(self):
        try: self.chunk.keyword = u"\u1234"
        except UnicodeError: pass
        else: self.fail("Invalid keyword was set.")

    def test_set_invalid_unicode_value(self):
        try: self.chunk.string = u"\u1234"
        except UnicodeError: pass
        else: self.fail("Invalid value was set.")

    def test_set_invalid_null_keyword(self):
        try: self.chunk.keyword = u"abc\x00def"
        except ValueError: pass
        else: self.fail("Invalid keyword was set.")

    def test_set_invalid_null_value(self):
        try: self.chunk.string = u"abc\x00def"
        except ValueError: pass
        else: self.fail("Invalid value was set.")

    def test_set_invalid_too_long_keyword(self):
        try: self.chunk.keyword = u"a" * 80
        except ValueError: pass
        else: self.fail("Invalid keyword was set.")

    def test_set_invalid_too_short_keyword(self):
        try: self.chunk.keyword = u""
        except ValueError: pass
        else: self.fail("Invalid keyword was set.")


add(TtEXt)
