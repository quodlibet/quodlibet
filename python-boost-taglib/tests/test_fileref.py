from unittest import TestCase
from taglib import FileRef

class FileRefOpen(TestCase):
    valid = FileRef("tests/data/silence-44-s.ogg")
    invalid = FileRef("/doesnotexist")

    def test_valid(self): self.failUnless(self.valid)
    def test_invalid(self): self.failIf(self.invalid)

cases = [FileRefOpen]
