import os, gtk
from tests import TestCase, add
from qltk.cbes import ComboBoxEntrySave
from StringIO import StringIO

class TComboBoxEntrySave(TestCase):
    def test_apprepend(self):
        c = ComboBoxEntrySave()
        self.failUnlessEqual([], c.get_text())
        c.append_text("line 1")
        c.append_text("line 2")
        c.prepend_text("line 0")
        self.failUnlessEqual(["line 0", "line 1", "line 2"], c.get_text())
        c.destroy()

    def test_initial(self):
        c = ComboBoxEntrySave(initial = ["line 1", "line 2"])
        self.failUnlessEqual(["line 1", "line 2"], c.get_text())
        c.destroy()

    def test_count(self):
        c = ComboBoxEntrySave(initial = ["line 1"], count = 2)
        self.failUnlessEqual(["line 1"], c.get_text())
        c.append_text("line 2")
        self.failUnlessEqual(["line 1", "line 2"], c.get_text())
        c.append_text("line 3")
        self.failUnlessEqual(["line 1", "line 2"], c.get_text())
        c.prepend_text("line 0")
        self.failUnlessEqual(["line 0", "line 1"], c.get_text())
        c.destroy()

    def test_read_filename(self):
        f = file("combo_test", "w")
        f.write("line 1\nline 2\nline 3\n")
        f.close()
        c = ComboBoxEntrySave("combo_test")
        self.failUnlessEqual(["line 1", "line 2", "line 3"], c.get_text())
        os.unlink("combo_test")
        c.destroy()

    def test_read_filelike(self):
        f = StringIO("line 1\nline 2\nline 3\n")
        c = ComboBoxEntrySave(f)
        self.failUnlessEqual(["line 1", "line 2", "line 3"], c.get_text())
        c.destroy()

    def test_write_filelike(self):
        f = StringIO()
        c = ComboBoxEntrySave(initial = ["line 1", "line 2", "line 3"])
        c.write(f)
        f.seek(0)
        c2 = ComboBoxEntrySave(f)
        self.failUnlessEqual(c.get_text(), c2.get_text())
        c.destroy()
        c2.destroy()

    def test_write_filename(self):
        c = ComboBoxEntrySave(initial = ["line 1", "line 2", "line 3"])
        c.write("combo_test")
        c2 = ComboBoxEntrySave("combo_test")
        self.failUnlessEqual(c.get_text(), c2.get_text())
        os.unlink("combo_test")
        c.destroy()
        c2.destroy()

    def test_write_filedir(self):
        self.failIf(os.path.isdir('notdir'))
        c = ComboBoxEntrySave(initial = ["line 1", "line 2", "line 3"])
        c.write("notdir/combo_test")
        c2 = ComboBoxEntrySave("notdir/combo_test")
        self.failUnlessEqual(c.get_text(), c2.get_text())
        os.unlink("notdir/combo_test")
        os.rmdir("notdir")
        c.destroy()
        c2.destroy()

    def test_initial_file_append(self):
        c = ComboBoxEntrySave(
            StringIO("line 0"), initial = ["line 1"])
        c.append_text("line 2")
        self.failUnlessEqual(["line 0", "line 1", "line 2"], c.get_text())
        c.destroy()
add(TComboBoxEntrySave)
