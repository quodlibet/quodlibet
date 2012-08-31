import gtk

from tests import TestCase, add
from quodlibet.qltk.getstring import GetStringDialog

class _ClipboadTestClass(GetStringDialog):
    _OK = True
    def _verify_clipboard(self, text):
        if self._OK:
            return text

class TGetStringDialog(TestCase):
    def setUp(self):
        self.gsd1 = GetStringDialog(None, "title", "enter a string")
        self.gsd2 = _ClipboadTestClass(None, "title", "enter a string",
                                       options=["1", "2"])

    def test_getstring(self):
        ret = self.gsd1.run(text="foobar", test=True)
        self.failUnlessEqual(ret, "foobar")

    def test_clipboard(self):
        clipboard = gtk.clipboard_get()
        clipboard.set_text("42", -1)
        ret = self.gsd2.run(text="24", clipboard=True, test=True)
        self.failUnlessEqual(ret, "42")

    def tearDown(self):
        self.gsd1.destroy()
        self.gsd2.destroy()

add(TGetStringDialog)
