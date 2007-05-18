from tests import TestCase, add

from quodlibet.qltk._editpane import FilterCheckButton

class FCB(FilterCheckButton):
    _section = _key = _label = "foo"

class FCB2(FCB): _order = 1.0
class FCB3(FCB): _order = 1.2
class FCB4(FCB): _order = 1.3
class FCB5(FCB): _order = 1.3
class FCB1(FCB): _order = 1.4

class TFilterCheckButton(TestCase):
    def setUp(self):
        self.fcb1 = FCB1()
        self.fcb2 = FCB2()
        self.fcb3 = FCB3()
        self.fcb4 = FCB4()
        self.fcb5 = FCB5()

    def test_filter(self):
        self.failUnlessRaises(NotImplementedError, self.fcb1.filter, "", "")

    def test_filter_list(self):
        self.failUnlessRaises(
            NotImplementedError, self.fcb1.filter_list, [""], [""])

    def test_cmp(self):
        l = [self.fcb1, self.fcb2, self.fcb3, self.fcb4, self.fcb5]
        l.sort()
        self.failUnlessEqual(
            l, [self.fcb2, self.fcb3, self.fcb4, self.fcb5, self.fcb1])

    def tearDown(self):
        for cb in [self.fcb1, self.fcb2, self.fcb3, self.fcb4, self.fcb5]:
            cb.destroy()
add(TFilterCheckButton)
