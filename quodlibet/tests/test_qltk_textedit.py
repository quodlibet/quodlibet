from tests import TestCase

from quodlibet.qltk.textedit import TextEditBox, TextEdit


class TTextEditBox(TestCase):
    def setUp(self):
        self.box = TextEditBox()

    def test_empty(self):
        self.failUnlessEqual(self.box.text, "")

    def test_set(self):
        self.box.text = "bazquux"
        self.failUnlessEqual(self.box.text, "bazquux")

    def test_clicked(self):
        self.box.apply.clicked()

    def tearDown(self):
        self.box.destroy()


class TTextEdit(TTextEditBox):
    def setUp(self):
        self.box = TextEdit(None)


class TTextEditBox2(TestCase):
    def setUp(self):
        self.foobar = TextEditBox("foobar")

    def test_revert(self):
        self.foobar.revert.clicked()
        self.failUnless(self.foobar.text, "foobar")

    def tearDown(self):
        self.foobar.destroy()


class TTextEdit2(TTextEditBox2):
    def setUp(self):
        self.foobar = TextEdit(None, "foobar")
