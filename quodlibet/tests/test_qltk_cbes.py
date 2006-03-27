import os
import tempfile

from tests import TestCase, add
from qltk.cbes import ComboBoxEntrySave

class TComboBoxEntrySave(TestCase):
    memory = "pattern 1\npattern 2\n"
    saved = "pattern text\npattern name\n"

    def setUp(self):
        self.fname = tempfile.mkstemp()[1]
        f = file(self.fname, "wU")
        f.write(self.memory)
        f.close()

        f = file(self.fname + ".saved", "wU")
        f.write(self.saved)
        f.close()
        self.cbes = ComboBoxEntrySave(self.fname, count=2, model=self.fname)
        self.cbes2 = ComboBoxEntrySave(self.fname, count=2, model=self.fname)

    def test_equivalence(self):
        rows1 = list(self.cbes.get_model())
        rows2 = list(self.cbes2.get_model())

        for row1, row2 in zip(rows1, rows2):
            self.failUnlessEqual(row1[0], row2[0])
            self.failUnlessEqual(row1[1], row2[1])
            self.failUnlessEqual(row1[2], row2[2])

    def test_shared_model(self):
        self.cbes.append_text("a test")
        self.test_equivalence()

    def test_initial_size(self):
        # 1 saved, Edit, separator, 2 remembered
        self.failUnlessEqual(5, len(self.cbes.get_model()))

    def test_prepend_text(self):
        self.cbes.prepend_text("pattern 3")
        self.memory = "pattern 3\npattern 1\n"
        self.test_save()

    def test_save(self):
        self.cbes.write()
        self.failUnlessEqual(self.memory, file(self.fname).read())
        self.failUnlessEqual(self.saved, file(self.fname + ".saved").read())

    def test_set_text_iter_magic(self):
        self.cbes.child.set_text("foobar")
        for row in self.cbes.get_model():
            if row[2] != None:
                self.failUnlessEqual("foobar", row[0])

    def tearDown(self):
        self.cbes.destroy()
        self.cbes2.destroy()
        os.unlink(self.fname)
        os.unlink(self.fname + ".saved")

add(TComboBoxEntrySave)
